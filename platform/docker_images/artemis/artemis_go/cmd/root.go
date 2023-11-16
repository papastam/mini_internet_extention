/*
Copyright © 2023 NAME HERE <EMAIL ADDRESS>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

	http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/
package cmd

import (
	"fmt"
	"github.com/common-nighthawk/go-figure"
	"github.com/spf13/cobra"
	"os"
)

var UpdateFile string
var PrefixFile string
var HijackFile string
var RelationsFile string
var LineNo int64
var Interval int64

var CommandProvided bool = false
var IntervalEnabled bool = false

// rootCmd represents the base command when called without any subcommands
var rootCmd = &cobra.Command{
	Use:   "ihd",
	Short: "A BGP hijack detector",
	Long:  `HCI is a BGP hijack detector witten in GO. It relies on historical data fetched with bgpreader and provided in a custom format.`,
	// Uncomment the following line if your bare application
	// has an action associated with it:
	//	Run: func(cmd *cobra.Command, args []string) { },
}

// Execute adds all child commands to the root command and sets flags appropriately.
// This is called by main.main(). It only needs to happen once to the rootCmd.
func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}

func init() {
	cobra.OnInitialize(initConfig)

	// Here you will define your flags and configuration settings.
	// Cobra supports persistent flags, which, if defined here,
	// will be global for your application.

	rootCmd.PersistentFlags().StringVar(&UpdateFile, "updates", "", "file containing bgp updates")

	// Cobra also supports local flags, which will only run
	// when this action is called directly.
	rootCmd.PersistentFlags().StringVar(&PrefixFile, "prefixes", "", "file containing prefix-to-as mappings")
	rootCmd.PersistentFlags().StringVar(&HijackFile, "output", "hijacks.csv", "file containing the detected hijacks")
	rootCmd.PersistentFlags().Int64Var(&LineNo, "lineno", 0, "the number of lines the update file contains ")
	rootCmd.PersistentFlags().StringVar(&RelationsFile, "relations", "", "CAIDA's graph for AS relationships ")
	// rootCmd.PersistentFlags().StringVar(&RelationsFile, "relations", "", "CAIDA's graph for AS relationships ")

	rootCmd.MarkPersistentFlagRequired("updates")
	rootCmd.MarkPersistentFlagRequired("prefixes")
	// rootCmd.MarkPersistentFlagRequired("relations")
}

// initConfig reads in config file and ENV variables if set.
func initConfig() {
	myFigure := figure.NewFigure("ARTEMIS DETECTOR", "", true)
	myFigure.Print()

}

