package main

import (
	"bufio"
	"encoding/csv"
	"fmt"
	"github.com/kentik/patricia"
	"github.com/kentik/patricia/string_tree"
	"github.com/mikioh/ipaddr"
	"io"
	"log"
	"net"
	"os"
	"strings"
	"time"
)

func getTimeDiffInSeconds(time1 float64, time2 float64) float64 {
	tm1 := time.Unix(int64(time1), 0)
	tm2 := time.Unix(int64(time2), 0)
	return tm2.Sub(tm1).Seconds()
}

func toPrefixes(IPs []string) []ipaddr.Prefix {
	if IPs == nil {
		return nil
	}
	var ps []ipaddr.Prefix
	for _, s := range IPs {
		_, n, err := net.ParseCIDR(s)
		if err != nil {
			return nil
		}
		ps = append(ps, *ipaddr.NewPrefix(n))
	}
	return ps
}

func lineCounter(filename string) int64 {
	file, err := os.Open(filename)
	if err != nil {
		fmt.Println("Err ", err)
	}
	scanner := bufio.NewScanner(file)
	var lines int64
	lines = 0
	for scanner.Scan() {
		lines++
	}
	return lines
}

func generatePeerGraph(filename string) map[string][]string {
	fileGraph, err := os.Open(filename)
	peer2peer := make(map[string][]string)

	if err != nil {
		log.Fatal(err)
	}

	defer func(fileGraph *os.File) {
		err := fileGraph.Close()
		if err != nil {

		}
	}(fileGraph)
	csvReader2 := csv.NewReader(fileGraph)
	csvReader2.Comma = '|'
	for {
		peerRecord, err := csvReader2.Read()
		if err == io.EOF {
			break
		}
		if strings.Contains(peerRecord[0], "#") || !strings.Contains(peerRecord[2], "-1") {
			continue
		}
		val, ok := peer2peer[peerRecord[0]]
		// If the key doesnt exist
		if !ok {
			val = []string{peerRecord[1]}
			peer2peer[peerRecord[0]] = val
		} else {
			peer2peer[peerRecord[0]] = append(val, peerRecord[1])
		}

		val2, ok2 := peer2peer[peerRecord[1]]
		// If the key doesnt exist
		if !ok2 {
			val2 = []string{peerRecord[0]}
			peer2peer[peerRecord[1]] = val2
		} else {
			peer2peer[peerRecord[1]] = append(val, peerRecord[0])
		}
	}

	return peer2peer
}

func getSuperNet(prefix string) ipaddr.Prefix {
	return *ipaddr.Supernet(toPrefixes([]string{
		prefix,
	}))
}

func generatePatriciaTree(filename string) (map[string][]string, *string_tree.TreeV4) {
	f, err := os.Open(filename)
	if err != nil {
		log.Fatal(err)
	}
	defer func(f *os.File) {
		err := f.Close()
		if err != nil {
			log.Fatal(err)
		}
	}(f)

	csvReader := csv.NewReader(f)
	csvReader.Comma = '|'
	_, err2 := csvReader.Read()
	if err2 != nil {
		log.Fatal(err2)
	}

	prefixTree := string_tree.NewTreeV4()
	prefixASMap := make(map[string][]string)

	for {
		rec, err := csvReader.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			log.Fatal(err)
		}

		prefix := rec[0]
		asn := rec[1]

		v4IP, _, err := patricia.ParseIPFromString(prefix)
		if err != nil {
			log.Fatal(err)
		}

		prefixTree.Add(*v4IP, fmt.Sprintf("%s_%s", prefix, asn), nil)
		sliceAS, prefixExists := prefixASMap[prefix]

		if prefixExists {
			prefixASMap[prefix] = append(sliceAS, asn)
		} else {
			prefixASMap[prefix] = make([]string, 0)
			prefixASMap[prefix] = append(prefixASMap[prefix], asn)
		}
	}

	return prefixASMap, prefixTree
}

func splitPrefixASN(key string) (string, []string) {
	split := strings.Split(key, "_")
	return split[0], split[1:]
}

func isSubset(subset []string, superset []string) bool {
	checkset := make(map[string]bool)
	for _, element := range subset {
		checkset[element] = true
	}
	for _, value := range superset {
		if checkset[value] {
			delete(checkset, value)
		}
	}
	return len(checkset) == 0 //this implies that set is subset of superset
}

func Find(slice []string, val string) (int, bool) {
	for i, item := range slice {
		if item == val {
			return i, true
		}
	}
	return -1, false
}

