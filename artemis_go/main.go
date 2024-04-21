package main

import (
	"bufio"
	"encoding/csv"
	"fmt"
	"io"
	"log"
	"math"
	"os"
	"os/exec"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/kentik/patricia"
	"github.com/kentik/patricia/string_tree"
	"github.com/schollz/progressbar/v3"
	"github.com/shanmukhsista/cliapp/cmd"
	"golang.org/x/exp/slices"
)

type HijackType string

const (
	SubPrefix   HijackType = "S|0|-|-"
	ExactPrefix HijackType = "E|0|-|-"
	Valid       HijackType = "valid"
	Undefined   HijackType = "undefined"
)

type Hijack struct {
	prefix          string
	hijack_as       string
	origin_as       string
	hj_type         HijackType
	time_started    float64
	time_last       float64
	time_ended      float64
	peers_seen      []string
	peers_withdrawn []string
	state           HijackState
	messageCount    int64
	mitigated       bool
}

type BGPUpdate struct {
	prefix      string
	messageType string
	origin_as   string
	timestamp   float64
	peer_as     string
	path        string
}

type HijackState string

const (
	Ongoing   HijackState = "Ongoing"
	Dormant   HijackState = "Dormant"
	Withdrawn HijackState = "Withdrawn"
	Mitigated HijackState = "Mitigated"
)

const messageCountThreshold = 0

var ongoingHijackMap map[string]Hijack

var detectedHijackMap map[string]Hijack

var mitigatedHijackMap map[string]Hijack

var prefixMap map[string]string

var prefixPeerMap map[string]string

var withdrawalsMap map[string]Hijack

var mitigatedPrefixes map[string]bool

var MitigationEnabled bool = false

func main() {
	c := make(chan os.Signal)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-c
		printHijacks()
		debug("Exiting...")
		os.Exit(1)
	}()

	cmd.Execute()
	if !cmd.CommandProvided {
		os.Exit(1)
	}
	// Initialize hash tables
	ongoingHijackMap = make(map[string]Hijack)
	detectedHijackMap = make(map[string]Hijack)
	mitigatedHijackMap = make(map[string]Hijack)
	prefixMap = make(map[string]string)
	prefixPeerMap = make(map[string]string)
	withdrawalsMap = make(map[string]Hijack)
	mitigatedPrefixes = make(map[string]bool)

	updatesFilename := cmd.UpdateFile
	prefixMapFilename := cmd.PrefixFile

	asn := cmd.Asn

	fmt.Println("")
	fmt.Println("Generating Peer Graph...")
	peerGraph := generatePeerGraph(prefixMapFilename)
	fmt.Println("Generating Patricia Tree...")
	prefixASMap, prefixTree := generatePatriciaTree(prefixMapFilename)

	if cmd.Interval != -1 { // Real-time hijack detection
		fmt.Print("Real-time hijack detection...\n")
		if cmd.MitigationScriptPath != "" {
			MitigationEnabled = true
		}

		// List with the last timestamp of each file
		var last_timestamps []float64
		var last_timestamp float64

		if cmd.InputType == "directory" {

			files, _ := os.ReadDir(updatesFilename)

			// Initialize the list with zeros
			for i := 0; i < len(files); i++ {
				last_timestamps = append(last_timestamps, 0)
			}
		}

		for {
			// Check for ongoing hijacks and mitigate them
			if MitigationEnabled {
				for _, hijack := range ongoingHijackMap {
					// if getTimeDiffInSeconds(hijack.time_last, float64(time.Now().UnixNano()/1000000)) > 600 {
					fmt.Printf("Detected hijack for prefix: %s\n", hijack.prefix)
					fmt.Printf("Mitigating the hijack...\n")
					mitigateHijack(hijack, asn)
					// }
				}
			}

			if cmd.InputType == "file" {
				fileUpdates, err := os.Open(updatesFilename)
				if err != nil {
					log.Fatal(err)
				}

				defer func(fileUpdates *os.File) {
					err := fileUpdates.Close()
					if err != nil {
						log.Fatal(err)
					}
				}(fileUpdates)

				last_timestamp = artemisDetection(asn, fileUpdates, prefixTree, prefixASMap, peerGraph, last_timestamp)

			} else if cmd.InputType == "directory" {

				// Get all files in the directory
				files, err := os.ReadDir(updatesFilename)
				if err != nil {
					log.Fatal(err)
				}

				// Iterate over all files in the directory
				for i, file := range files {
					fmt.Printf("Processing file: %s\n", file.Name())
					fileUpdates, err := os.Open(fmt.Sprintf("%s/%s", updatesFilename, file.Name()))
					if err != nil {
						log.Fatal(err)
					}

					last_timestamps[i] = artemisDetection(asn, fileUpdates, prefixTree, prefixASMap, peerGraph, last_timestamps[i])
				}
			}
			// Sleep for the specified interval
			fmt.Printf("Sleeping for %d minutes...\n", cmd.Interval)
			time.Sleep(time.Duration(cmd.Interval) * time.Minute)
		}

	} else { // Historical hijack detection
		if cmd.InputType == "file" {
			fileUpdates, err := os.Open(updatesFilename)
			if err != nil {
				log.Fatal(err)
			}

			defer func(fileUpdates *os.File) {
				err := fileUpdates.Close()
				if err != nil {
					log.Fatal(err)
				}
			}(fileUpdates)

			if cmd.SpecificAsn {
				artemisDetection(asn, fileUpdates, prefixTree, prefixASMap, peerGraph, 0)
			} else {
				artemisDetection(0, fileUpdates, prefixTree, prefixASMap, peerGraph, 0)
			}
		} else if cmd.InputType == "directory" {

			// Get all files in the directory
			files, err := os.ReadDir(updatesFilename)
			if err != nil {
				log.Fatal(err)
			}

			// Iterate over all files in the directory
			for _, file := range files {
				fmt.Printf("Processing file: %s\n", file.Name())
				fileUpdates, err := os.Open(fmt.Sprintf("%s/%s", updatesFilename, file.Name()))
				if err != nil {
					log.Fatal(err)
				}

				if cmd.SpecificAsn {
					artemisDetection(asn, fileUpdates, prefixTree, prefixASMap, peerGraph, 0)
				} else {
					artemisDetection(0, fileUpdates, prefixTree, prefixASMap, peerGraph, 0)
				}
			}
		}
	}

	printHijacks()
}

func artemisDetection(asn int64, fileUpdates *os.File, prefixTree *string_tree.TreeV4, prefixASMap map[string][]string, peerGraph map[string][]string, offset float64) float64 {
	csvReader2 := csv.NewReader(fileUpdates)
	csvReader2.Comma = '|'
	debug("Initiating Hijack Detection...")

	bar := progressbar.Default(cmd.LineNo)
	final_timestamp := float64(0)
	counter := 0

	// If offset!=0 seek the timestamp specified
	if offset != 0 {
		debug(fmt.Sprintf("Seeking to timestamp: %f", offset))
		for {
			updateRecord, err := csvReader2.Read()
			if err == io.EOF {
				break
			}
			s, _ := strconv.ParseFloat(updateRecord[8], 64)
			if s > offset {
				break
			}
		}
	}

	for {
		updateRecord, err := csvReader2.Read()
		if err == io.EOF {
			debug("No new updates found!")
			break
		}
		counter++

		// An example string:
		// 2a09:10c0::/29|6886|34927|34927 13249 6886|ris|rrc03|A|"[{""asn"":34927
		// PREFIX | ORIGIN AS | PEER AS | PATH | COLLECTOR | PEER | MESSAGE TYPE | MESSAGE
		var updateMessage BGPUpdate
		updateMessage.prefix = updateRecord[0]
		updateMessage.origin_as = updateRecord[1]
		updateMessage.peer_as = updateRecord[2]
		updateMessage.messageType = updateRecord[6]
		bar.Add(1)

		// if the prefix does not belong to the AS we are interested in, we skip it
		if asn != 0 {
			if !prefixBelongsToAS(updateMessage.prefix, asn, peerGraph) {
				continue
			}
		}

		if len(updateRecord) < 9 {
			continue
		}
		if s, err := strconv.ParseFloat(updateRecord[8], 64); err == nil {
			updateMessage.timestamp = s
			final_timestamp = s
		} else {
			continue
		}

		updateMessage.path = updateRecord[3]

		if strings.Contains(updateMessage.prefix, ":") || strings.Contains(updateRecord[1], "{") {
			continue
		}
		hijackType, hijackerAs, _, updateMessage, asnOrigin, prefixMatched := getHijackDetectionStatus(updateMessage, prefixTree, prefixASMap, peerGraph)
		// debug(getHijackDetectionStatus(updateMessage, prefixTree, prefixASMap, peerGraph))
		debug(fmt.Sprintln("Handling update message: ", updateMessage))
		debug(fmt.Sprintln("Hijack type: ", hijackType))
		if hijackType == Undefined {
			continue
		}

		hijack_key := ""
		if updateMessage.messageType == "A" {
			if hijackType != Valid {
				hijack_key = handleAnnouncement(updateMessage, hijackType, hijackerAs, asnOrigin, prefixMatched, peerGraph)
			} else {
				handleCorrectionAnnouncement(updateMessage, hijackType, hijackerAs, asnOrigin, prefixMatched, peerGraph)
			}
		} else { // Withdrawal message
			debug("Handling withdrawal")
			handleWithdrawal(updateMessage, prefixMatched)
		}
		if hijack_key != "" {
			debug(fmt.Sprintln("Hijack key: ", hijack_key))
		}
		if cmd.DebugEnabled {
			printStatus()
		}
	}
	debug(fmt.Sprintln("Total number of updates processed: ", counter))

	// return last message's timestamp
	if final_timestamp == 0 {
		return offset
	}
	return final_timestamp
}

func handleMitigation(updateMessage BGPUpdate, prefixMatched string, asnOrigin string, hijackerAs string, peerGraph map[string][]string) {
	markHijackMitigated := func(hijackKey string, hijack Hijack, termination_timestamp float64) {
		hijack.state = Mitigated
		hijack.time_ended = termination_timestamp
		mitigatedHijackMap[hijackKey] = hijack
		if hijack.messageCount > messageCountThreshold {
			detectedHijackMap[hijackKey+"_"+fmt.Sprintf("%f", hijack.time_started)] = hijack
		}
		delete(ongoingHijackMap, hijackKey)
		delete(prefixMap, updateMessage.prefix)
	}

	// Check for the complemetary prefix
	debug("Handling mitigation")
	complementPrefix := calculateComplementarySubnet(prefixMatched)
	_, complementPrefixExists := mitigatedPrefixes[complementPrefix]

	if complementPrefixExists {
		debug("Mitigation detected, complement prefix exists")
		// Calculate supernet
		superNet := calculateSupernet(prefixMatched, complementPrefix)
		if superNet == "" {
			debug("Could not calculate supernet")
			return
		}

		for key, _ := range ongoingHijackMap {
			if ongoingHijackMap[key].prefix == superNet {
				hijack := ongoingHijackMap[key]
				hijack.mitigated = true
				ongoingHijackMap[key] = hijack
				debug(fmt.Sprintln("Hijack", key, "marked as mitigated"))
				markHijackMitigated(key, hijack, updateMessage.timestamp)
			}
		}

		// Remove the prefix from the mitigated prefixes
		delete(mitigatedPrefixes, complementPrefix)
	} else {
		debug("Mitigation detected, complement prefix does not exist")
		_, prefixExists := prefixMap[prefixMatched]
		if !prefixExists {
			// Add the prefix to the mitigated prefixes
			mitigatedPrefixes[prefixMatched] = true
			debug(fmt.Sprintln("Prefix", prefixMatched, "added to mitigated prefixes"))
		}
	}
}

func handleWithdrawal(updateMessage BGPUpdate, prefixMatched string) {
	markHijackTermination := func(hijackKey string, hijack Hijack) {
		hijack.state = Withdrawn
		hijack.time_ended = hijack.time_last
		//withdrawalKey := fmt.Sprintf("%s_%s_%s", updateMessage.prefix, hijack_as, hijack_type)

		withdrawalsMap[hijackKey] = hijack
		if hijack.messageCount > messageCountThreshold {
			detectedHijackMap[hijackKey+"_"+fmt.Sprintf("%f", hijack.time_started)] = hijack
		}
		delete(ongoingHijackMap, hijackKey)
		delete(prefixMap, updateMessage.prefix)
	}

	hijackKey, prefixExists := prefixMap[prefixMatched]
	_, keyExists := withdrawalsMap[hijackKey]

	if prefixExists && !keyExists {
		h := ongoingHijackMap[hijackKey]
		if !slices.Contains(h.peers_withdrawn, updateMessage.peer_as) {
			h.peers_withdrawn = append(h.peers_withdrawn, updateMessage.peer_as)
			ongoingHijackMap[hijackKey] = h
		}

		if isSubset(h.peers_seen, h.peers_withdrawn) {
			if getTimeDiffInSeconds(h.time_last, updateMessage.timestamp) > 60 {
				markHijackTermination(hijackKey, h)
			} else {
				h.state = Withdrawn
				if h.messageCount > messageCountThreshold {
					detectedHijackMap[hijackKey+"_"+fmt.Sprintf("%f", h.time_started)] = h
				}
			}
		}
	}
}

func handleAnnouncement(updateMessage BGPUpdate, hijack_type HijackType, hijack_as string, asnOrigin string, prefixMatched string, peerGraph map[string][]string) string {
	hijackKey := fmt.Sprintf("%s_%s_%s", prefixMatched, updateMessage.origin_as, hijack_type)
	hijackVal, ok := ongoingHijackMap[hijackKey]

	var h Hijack
	h.prefix = updateMessage.prefix
	h.origin_as = updateMessage.origin_as
	h.hj_type = hijack_type
	h.hijack_as = hijack_as
	timestamp := updateMessage.timestamp
	h.time_ended = -1
	h.time_started = timestamp
	h.time_last = timestamp
	h.peers_seen = hijackVal.peers_seen
	h.peers_withdrawn = hijackVal.peers_withdrawn
	h.messageCount = 1

	prefixPeerMap[fmt.Sprintf("%s_%s", updateMessage.prefix, updateMessage.peer_as)] = updateMessage.prefix

	if !slices.Contains(h.peers_seen, updateMessage.peer_as) {
		h.peers_seen = append(h.peers_seen, updateMessage.peer_as)
	}
	// If the key exists
	if ok {
		debug(fmt.Sprintln("Key exists:", hijackKey))
		h.messageCount = hijackVal.messageCount + 1
		if isSubset(hijackVal.peers_seen, hijackVal.peers_withdrawn) {
			if getTimeDiffInSeconds(hijackVal.time_last, timestamp) > 600 {
				if hijackVal.messageCount > messageCountThreshold {
					hijackVal.state = Withdrawn
					hijackVal.time_ended = hijackVal.time_last + 600*1000
					detectedHijackMap[hijackKey+"_"+fmt.Sprintf("%f", hijackVal.time_started)] = hijackVal
				}
				h.time_started = math.Min(float64(timestamp), float64(hijackVal.time_started))
				h.time_last = math.Max(float64(float32(timestamp)), float64(hijackVal.time_last))
				ongoingHijackMap[hijackKey] = h
			} else {
				h.state = Withdrawn
				h.time_started = math.Min(float64(timestamp), float64(hijackVal.time_started))
				h.time_last = math.Max(float64(float32(timestamp)), float64(hijackVal.time_last))
				ongoingHijackMap[hijackKey] = h
			}
		} else {
			h.state = Ongoing
			h.time_started = math.Min(float64(timestamp), float64(hijackVal.time_started))
			h.time_last = math.Max(float64(float32(timestamp)), float64(hijackVal.time_last))
			ongoingHijackMap[hijackKey] = h
		}
	} else {
		h.messageCount = 1
		prefixMap[prefixMatched] = hijackKey
		ongoingHijackMap[hijackKey] = h
	}
	return hijackKey
}

func handleCorrectionAnnouncement(updateMessage BGPUpdate, hijack_type HijackType, hijack_as string, asnOrigin string, prefixMatched string, peerGraph map[string][]string) {
	markHijackTermination := func(hijackKey string, hijack Hijack) {
		hijack.state = Withdrawn
		hijack.time_ended = hijack.time_last
		//withdrawalKey := fmt.Sprintf("%s_%s_%s", updateMessage.prefix, hijack_as, hijack_type)

		withdrawalsMap[hijackKey] = hijack
		if hijack.messageCount > messageCountThreshold {
			detectedHijackMap[hijackKey+"_"+fmt.Sprintf("%f", hijack.time_started)] = hijack
		}
		delete(ongoingHijackMap, hijackKey)
		delete(prefixMap, updateMessage.prefix)
	}

	as_number, _ := strconv.ParseInt(updateMessage.origin_as, 10, 64)
	// Handle implicit withdrawal
	debug(fmt.Sprintln(peerGraph[updateMessage.origin_as][0], "==", updateMessage.prefix))
	if peerGraph[updateMessage.origin_as][0] == updateMessage.prefix {
		for key, _ := range ongoingHijackMap {
			split := strings.Split(key, "_")
			prefix := split[0]

			// If the route is valid for an ongoing hijack then we terminate the hijack
			if prefix == updateMessage.prefix {
				debug("Handling implicit withdrawal")
				markHijackTermination(key, ongoingHijackMap[key])
			}
		}
	} else if prefixBelongsToAS(updateMessage.prefix, as_number, peerGraph) { //Handle mitigation
		debug("Handling mitigation")
		handleMitigation(updateMessage, updateMessage.prefix, asnOrigin, hijack_as, peerGraph)
	}
}

func isOriginValid(validASes []string, updateMessage BGPUpdate) bool {
	_, found := Find(validASes, updateMessage.origin_as)
	return found
}

func getHijackDetectionStatus(updateMessage BGPUpdate, prefixTree *string_tree.TreeV4, prefixASMap map[string][]string, peerGraph map[string][]string) (HijackType, string, bool, BGPUpdate, string, string) {
	var isPartialPrefixMatch bool
	var treeMatchedASN string
	var validPrefix string
	var validOriginASNS []string

	exactMatchASN, isExactPrefixMatch := prefixASMap[updateMessage.prefix]

	hijackType := Valid
	hijackerAs := "-1"
	isHijack := false
	v4IP, _, _ := patricia.ParseIPFromString(updateMessage.prefix)
	isPartialPrefixMatch, treeMatchedASN = prefixTree.FindDeepestTag(*v4IP)

	if !isPartialPrefixMatch {
		hijackType = Undefined
		return hijackType, hijackerAs, false, updateMessage, "", validPrefix
	} else if isExactPrefixMatch && !isOriginValid(exactMatchASN, updateMessage) && len(updateMessage.path) != 0 {
		hijackType = ExactPrefix
		hijackerAs = updateMessage.origin_as
		validPrefix = updateMessage.prefix
		isHijack = true
	} else if updateMessage.messageType == "W" {
		if isPartialPrefixMatch && !isExactPrefixMatch {
			validPrefix, validOriginASNS = splitPrefixASN(treeMatchedASN)

			if !isOriginValid(validOriginASNS, updateMessage) {
				peers, existsInPeerGraph := peerGraph[updateMessage.origin_as]
				if existsInPeerGraph {
					isPeer := false
					for _, asn := range validOriginASNS {
						_, isPeer = Find(peers, asn)
						if isPeer {
							break
						}
					}
					if !isPeer {
						hijackType = SubPrefix
						hijackerAs = updateMessage.origin_as
						isHijack = true
					}
				} else {
					hijackType = SubPrefix
					hijackerAs = updateMessage.origin_as
					isHijack = true
				}
			}
		}

		if !isHijack {
			superNet := getSuperNet(updateMessage.prefix).String()

			_, okPref := prefixPeerMap[fmt.Sprintf("%s_%s", updateMessage.prefix, updateMessage.peer_as)]
			_, okSuperPref := prefixPeerMap[fmt.Sprintf("%s_%s", superNet, updateMessage.peer_as)]

			// implicit withdrawal
			if okPref || okSuperPref {
				updateMessage.messageType = "W"
				if okSuperPref {
					updateMessage.prefix = superNet
					// delete(prefixPeerMap, fmt.Sprintf("%s_%s", sp, updateMessage.peer_as))
				} else {
					// delete(prefixPeerMap, fmt.Sprintf("%s_%s", updateMessage.prefix, updateMessage.peer_as))
				}
			}
		}
	} else {
		if isPartialPrefixMatch && !isExactPrefixMatch {
			// Check if the sub-prefix is a valid sub-prefix of a valid as
			hijackerAs = updateMessage.origin_as
			AS_number, _ := strconv.ParseInt(updateMessage.origin_as, 10, 64)
			validPrefix = updateMessage.prefix
			if !prefixBelongsToAS(validPrefix, AS_number, peerGraph) {
				hijackType = SubPrefix
				isHijack = true
			} else {
				isHijack = false
				hijackType = Valid
			}
		}
	}

	asnOrigin := ""
	if isExactPrefixMatch {
		asnOrigin = exactMatchASN[0]
	} else {
		if isPartialPrefixMatch {
			asnOrigin = treeMatchedASN
		}
	}

	return hijackType, hijackerAs, isHijack, updateMessage, asnOrigin, validPrefix
}

func mitigateHijack(hijack Hijack, as int64) {
	// Call the script specified in the arguements to mitigate the hijack
	debug(fmt.Sprintf("Calling: %s -p %s -a %d", cmd.MitigationScriptPath, hijack.prefix, as))
	out, out2 := exec.Command(cmd.MitigationScriptPath, "-p", hijack.prefix, "-a", strconv.FormatInt(as, 10)).Output()

	fmt.Printf("Mitigation script output:\n %s", out)
	fmt.Printf("End of mitigation script output.\n")
	debug(fmt.Sprintf("Error Output: %s", out2))
}

func printStatus() {
	// Calculate terminated hijacks
	terminatedHijacks := len(detectedHijackMap) - len(ongoingHijackMap)
	if terminatedHijacks < 0 {
		terminatedHijacks = 0
	}

	fmt.Printf("We have detected %d hijacks:\n", len(detectedHijackMap))
	fmt.Printf("	- %d ongoing hijacks\n", len(ongoingHijackMap))
	fmt.Printf("	- %d terminated hijacks\n", terminatedHijacks)
	fmt.Printf("	- %d mitigated prefixes\n", len(mitigatedHijackMap))
}

func printHijacks() {
	printStatus()

	file, err := os.Create(cmd.HijackFile)
	if err != nil {
		log.Fatalf("failed creating file: %s", err)
	}

	datawriter := bufio.NewWriter(file)
	datawriter.WriteString("prefix,origin as,hijack type,hijacker asn,time started,time of last update,time ended,state,duration\n")

	for _, hijack := range detectedHijackMap {
		if hijack.state == Withdrawn {
			hijack.time_ended = hijack.time_last
		} else {
			// hijack.state = Dormant
			hijack.time_ended = hijack.time_last + 600
		}

		hijackLine := fmt.Sprintf("%s,%s,%s,%s,%f,%f,%f,%s,%f\n", hijack.prefix, hijack.origin_as, hijack.hj_type, hijack.hijack_as, hijack.time_started,
			hijack.time_last, hijack.time_ended, hijack.state, getTimeDiffInSeconds(hijack.time_started, hijack.time_ended)/60)
		_, _ = datawriter.WriteString(hijackLine)
	}

	// Print ongoing hijacks
	for _, hijack := range ongoingHijackMap {
		// hijack.state = Dormant
		hijack.time_ended = hijack.time_last + 600
		// WHY IS THIS NEEDED?
		// if hijack.time_started != hijack.time_last {
		hijackLine := fmt.Sprintf("%s,%s,%s,%s,%f,%f,%f,%s,%f\n", hijack.prefix, hijack.origin_as, hijack.hj_type, hijack.hijack_as, hijack.time_started,
			hijack.time_last, hijack.time_ended, hijack.state, getTimeDiffInSeconds(hijack.time_started, hijack.time_ended)/60)
		_, _ = datawriter.WriteString(hijackLine)
		// }
	}

	// Print mitigated hijacks
	for _, hijack := range mitigatedHijackMap {
		hijack.state = Mitigated
		hijack.time_ended = hijack.time_last + 600
		hijackLine := fmt.Sprintf("%s,%s,%s,%s,%f,%f,%f,%s,%f\n", hijack.prefix, hijack.origin_as, hijack.hj_type, hijack.hijack_as, hijack.time_started,
			hijack.time_last, hijack.time_ended, hijack.state, getTimeDiffInSeconds(hijack.time_started, hijack.time_ended)/60)
		_, _ = datawriter.WriteString(hijackLine)
	}

	datawriter.Flush()
}

func debug(message string) {
	if cmd.DebugEnabled {
		fmt.Println(message)
	}
}
