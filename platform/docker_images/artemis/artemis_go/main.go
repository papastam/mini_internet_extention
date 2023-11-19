package main

import (
	"bufio"
	"encoding/csv"
	"fmt"
	"io"
	"log"
	"math"
	"os"
	"strconv"
	"strings"
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
)

const messageCountThreshold = 0

var ongoingHijackMap map[string]Hijack

var detectedHijackMap map[string]Hijack

var prefixMap map[string]string

var prefixPeerMap map[string]string

var withdrawalsMap map[string]Hijack

var MitigationEnabled bool = false

func main() {
	cmd.Execute()
	if !cmd.CommandProvided {
		os.Exit(1)
	}
	// Initialize hash tables
	ongoingHijackMap = make(map[string]Hijack)
	detectedHijackMap = make(map[string]Hijack)
	prefixMap = make(map[string]string)
	prefixPeerMap = make(map[string]string)
	withdrawalsMap = make(map[string]Hijack)

	updatesFilename := cmd.UpdateFile
	prefixMapFilename := cmd.PrefixFile

	pipe := &os.File{}

	debug("Updates file: " + updatesFilename)
	debug("Prefixes file: " + prefixMapFilename)
	debug("Hijack file: " + cmd.HijackFile)

	fmt.Println("")
	fmt.Println("Generating Peer Graph...")
	peerGraph := generatePeerGraph(prefixMapFilename)
	fmt.Println("Generating Patricia Tree...")
	prefixASMap, prefixTree := generatePatriciaTree(prefixMapFilename)

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

	if cmd.IntervalEnabled == true {
		var Asn int64 = -1

		if cmd.Asn != -1 {
			// open the named pipe
			pipeName := cmd.PipeName
			pipe, err = os.OpenFile(pipeName, os.O_WRONLY, os.ModeNamedPipe)
			if err != nil {
				fmt.Println("Error opening pipe: ", err)
				fmt.Println("Continuing with hijack detection without mitigation...")
				MitigationEnabled = false
				Asn = -1
			} else {
				Asn = cmd.Asn
				fmt.Println("Mitigating hijacks for AS", Asn)
				MitigationEnabled = true
			}
		}

		interval := cmd.Interval
		timestamp_last := float64(0)

		// Run the detection for the first time
		fmt.Println("Parsing file from the beginning...")

		csvReader2 := csv.NewReader(fileUpdates)
		csvReader2.Comma = '|'
		timestamp_last = artemisDetection(csvReader2, prefixTree, prefixASMap, peerGraph)

		mitigateHijacks(Asn, pipe, peerGraph)

		fmt.Println("Sleeping for", interval, "seconds...")
		time.Sleep(time.Duration(interval) * time.Second)

		for {
			// Create a reader and start from the top of the file
			fileUpdates.Seek(0, 0)
			csvReader2 := csv.NewReader(fileUpdates)
			csvReader2.Comma = '|'

			fmt.Println("Parsing Updates after timestamp: ", timestamp_last)
			// advance the csvReader2 until the last timestamp
			for {
				// Read the next line
				updateRecord, err := csvReader2.Read()
				if err == io.EOF {
					break
				}
				// If the timestamp is equal to the last timestamp, break
				if red_ts, err := strconv.ParseFloat(updateRecord[8], 64); err == nil {
					if red_ts == timestamp_last {
						break
					}
				} else {
					continue
				}
			}

			temp_timestamp_last := artemisDetection(csvReader2, prefixTree, prefixASMap, peerGraph)
			if temp_timestamp_last != 0 {
				fmt.Println("Last timestamp: ", temp_timestamp_last)
				timestamp_last = temp_timestamp_last
			}

			mitigateHijacks(Asn, pipe, peerGraph)

			fmt.Println("Sleeping for", interval, "seconds...")
			time.Sleep(time.Duration(interval) * time.Second)
		}

	} else {

		csvReader2 := csv.NewReader(fileUpdates)
		csvReader2.Comma = '|'
		fmt.Println("Initiating Hijack Detection...")

		artemisDetection(csvReader2, prefixTree, prefixASMap, peerGraph)
	}

	// Close the opened files
	fileUpdates.Close()
	if MitigationEnabled {
		pipe.Close()
	}

}

func mitigateHijacks(Asn int64, pipe *os.File, peerGraph map[string][]string) {
	if MitigationEnabled {
		for hijack_key, hijack := range ongoingHijackMap {
			if hijack.state != Withdrawn && prefixBelongsToAS(hijack.prefix, Asn, peerGraph) && !hijack.mitigated {
				fmt.Println("Mitigating hijack: ", hijack_key)
				subnet1, subnet2 := calculateSubnets(hijack.prefix)

				// Write the mitigation commands to the named pipe
				_, err := pipe.WriteString(fmt.Sprintf("advertise %d %s null0\n", Asn, subnet1))
				if err != nil {
					log.Fatal("Error writing to pipe: ", err)
				}

				_, err = pipe.WriteString(fmt.Sprintf("advertise %d %s null0\n", Asn, subnet2))
				if err != nil {
					log.Fatal("Error writing to pipe: ", err)
				}

				hijack.mitigated = true
				ongoingHijackMap[hijack_key] = hijack
			}
		}
	}
}

func artemisDetection(csvReader2 *csv.Reader, prefixTree *string_tree.TreeV4, prefixASMap map[string][]string, peerGraph map[string][]string) float64 {
	bar := progressbar.Default(cmd.LineNo)
	final_timestamp := float64(0)
	counter := 0
	for {
		updateRecord, err := csvReader2.Read()
		if err == io.EOF {
			fmt.Println("No new updates found!")
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
		// fmt.Println(getHijackDetectionStatus(updateMessage, prefixTree, prefixASMap, peerGraph))
		if hijackType == Undefined {
			continue
		}

		if updateMessage.messageType == "A" {
			if hijackType != Valid {
				handleAnnouncement(updateMessage, hijackType, hijackerAs, asnOrigin, prefixMatched)
			} else {
				handleCorrectionAnnouncement(updateMessage, hijackType, hijackerAs, asnOrigin, prefixMatched)
			}
		} else { // Withdrawal message
			handleWithdrawal(updateMessage, prefixMatched)
		}
	}
	printHijacks()
	fmt.Println("Total number of updates processed: ", counter)

	// return last message's timestamp
	return final_timestamp
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

func handleAnnouncement(updateMessage BGPUpdate, hijack_type HijackType, hijack_as string, asnOrigin string, prefixMatched string) {
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
}

func handleCorrectionAnnouncement(updateMessage BGPUpdate, hijack_type HijackType, hijack_as string, asnOrigin string, prefixMatched string) {
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

	for key, _ := range ongoingHijackMap {
		split := strings.Split(key, "_")
		prefix := split[0]

		// If the route is valid for an ongoing hijack then we terminate the hijack
		if prefix == prefixMatched {
			markHijackTermination(key, ongoingHijackMap[key])
		}
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
				hijackType = Undefined
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

func printHijacks() {
	fmt.Printf("We have detected %d withdrawn hijacks\n", len(detectedHijackMap))
	fmt.Printf("We have detected %d ongoing hijacks\n", len(ongoingHijackMap))

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
			hijack.state = Dormant
			hijack.time_ended = hijack.time_last + 600
		}

		hijackLine := fmt.Sprintf("%s,%s,%s,%s,%f,%f,%f,%s,%f,%d,%d,%d\n", hijack.prefix, hijack.origin_as, hijack.hj_type, hijack.hijack_as, hijack.time_started,
			hijack.time_last, hijack.time_ended, hijack.state, getTimeDiffInSeconds(hijack.time_started, hijack.time_ended)/60, hijack.messageCount, hijack.peers_withdrawn, hijack.peers_seen)
		_, _ = datawriter.WriteString(hijackLine)
	}

	// Print ongoing hijacks
	for _, hijack := range ongoingHijackMap {
		hijack.state = Dormant
		hijack.time_ended = hijack.time_last + 600
		// WHY IS THIS NEEDED?
		// if hijack.time_started != hijack.time_last {
		hijackLine := fmt.Sprintf("%s,%s,%s,%s,%f,%f,%f,%s,%f,%d,%d,%d\n", hijack.prefix, hijack.origin_as, hijack.hj_type, hijack.hijack_as, hijack.time_started,
			hijack.time_last, hijack.time_ended, hijack.state, getTimeDiffInSeconds(hijack.time_started, hijack.time_ended)/60, hijack.messageCount, hijack.peers_withdrawn, hijack.peers_seen)
		_, _ = datawriter.WriteString(hijackLine)
		// }
	}
	datawriter.Flush()
}

func debug(message string) {
	if cmd.DebugEnabled {
		fmt.Println(message)
	}
}
