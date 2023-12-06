package main

import (
	"bufio"
	"encoding/binary"
	"encoding/csv"
	"fmt"
	"io"
	"log"
	"net"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/kentik/patricia"
	"github.com/kentik/patricia/string_tree"
	"github.com/mikioh/ipaddr"
)

func prefixBelongsToAS(prefix string, Asn int64, peerGraph map[string][]string) bool {
	// Parse the prefix into an IPNet
	_, advertNet, _ := net.ParseCIDR(prefix)

	// Get the asPrefixes belonging to the AS
	asPrefixes, _ := peerGraph[strconv.FormatInt(Asn, 10)]

	// Check if the given prefix is a sub-prefix of any of the prefixes belonging to the AS
	for _, as_prefix := range asPrefixes {
		_, as_network, _ := net.ParseCIDR(as_prefix)
		if as_network.Contains(advertNet.IP) {
			return true
		}
	}
	return false
}

func calculateSubnets(prefix string) (subnet1 string, subnet2 string) {
	// Split the prefix into the network address and the subnet mask
	ip, ipNet, _ := net.ParseCIDR(prefix)
	network := ip.Mask(ipNet.Mask)

	// Convert the network address to an integer
	networkInt := binary.BigEndian.Uint32(network)

	// Calculate the number of bits in the subnet mask
	ones, _ := ipNet.Mask.Size()

	// Calculate the bit needed to flip to get the second subnet
	flipBit := uint32(1 << (31 - ones))

	// Calculate the network address of each subnet
	subnet1Int := networkInt
	subnet2Int := networkInt + uint32(flipBit)

	// Convert the network addresses of the subnets back to the dotted decimal notation
	subnet1 = fmt.Sprintf("%s/%d", net.IPv4(uint32ToBytes(subnet1Int>>24), uint32ToBytes(subnet1Int>>16&0xFF), uint32ToBytes(subnet1Int>>8&0xFF), uint32ToBytes(subnet1Int&0xFF)).String(), ones+1)
	subnet2 = fmt.Sprintf("%s/%d", net.IPv4(uint32ToBytes(subnet2Int>>24), uint32ToBytes(subnet2Int>>16&0xFF), uint32ToBytes(subnet2Int>>8&0xFF), uint32ToBytes(subnet2Int&0xFF)).String(), ones+1)

	return subnet1, subnet2
}

func calculateComplementarySubnet(prefix1 string) (subnet string) {
	// Split the prefix into the network address and the subnet mask
	ip, ipNet, _ := net.ParseCIDR(prefix1)
	network := ip.Mask(ipNet.Mask)

	// Convert the network address to an integer
	networkInt := binary.BigEndian.Uint32(network)

	// Calculate the number of bits in the subnet mask
	ones, _ := ipNet.Mask.Size()

	// Calculate the bit needed to flip to get the second subnet
	compl_address := networkInt ^ (1 << (32 - ones))

	// Convert the network addresses of the subnets back to the dotted decimal notation
	subnet = fmt.Sprintf("%s/%d", net.IPv4(uint32ToBytes(compl_address>>24), uint32ToBytes(compl_address>>16&0xFF), uint32ToBytes(compl_address>>8&0xFF), uint32ToBytes(compl_address&0xFF)).String(), ones)

	return subnet
}

// The following conditions must be true for a prefix to be a sub-prefix of another prefix:
// 1. The sub-prefixes must have the same mask length
// 2. The sub-prefixes must have the same host bits
// 3. The LS bit of the network part of each address must be different
func calculateSupernet(prefix1 string, prefix2 string) (supernet string) {
	// Split the prefix into the network address and the subnet mask
	ip1, ipNet1, _ := net.ParseCIDR(prefix1)
	network1 := ip1.Mask(ipNet1.Mask)
	ip2, ipNet2, _ := net.ParseCIDR(prefix2)
	network2 := ip2.Mask(ipNet2.Mask)

	// Calculate the number of bits in the subnet mask
	networkSize, _ := ipNet1.Mask.Size()
	networkSize2, _ := ipNet2.Mask.Size()
	if networkSize2 != networkSize {
		return ""
	}

	networkInt1 := binary.BigEndian.Uint32(network1)
	networkInt2 := binary.BigEndian.Uint32(network2)

	// Calculate the host bits of each subnet
	host_part1 := networkInt1 & (1<<uint32(32-networkSize) - 1)
	host_part2 := networkInt2 & (1<<uint32(32-networkSize) - 1)
	if host_part1 != host_part2 {
		return ""
	}

	// Commpare the LS bit of the network part of each address
	network_part1 := networkInt1 >> uint32(32-networkSize)
	network_part2 := networkInt2 >> uint32(32-networkSize)
	if network_part1&1 == network_part2&1 {
		return ""
	}

	// Calculate the network address of the supernet
	supernetMask := networkSize - 1
	supernetInt := (networkInt1 >> (32 - supernetMask)) << (32 - supernetMask)

	// Convert the network addresses of the subnets back to the dotted decimal notation
	supernet = fmt.Sprintf("%s/%d", net.IPv4(uint32ToBytes(supernetInt>>24), uint32ToBytes(supernetInt>>16&0xFF), uint32ToBytes(supernetInt>>8&0xFF), uint32ToBytes(supernetInt&0xFF)).String(), supernetMask)
	return supernet
}

func uint32ToBytes(n uint32) byte {
	return byte(n & 0xff)
}

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
		if strings.Contains(peerRecord[0], "#") || strings.Contains(peerRecord[2], "-1") {
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
