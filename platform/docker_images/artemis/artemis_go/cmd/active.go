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
	"github.com/spf13/cobra"
)

// activeCmd
var activeCmd = &cobra.Command{
	Use:   "active",
	Short: "Run hijack detection at a specified interval and mitigate hijacks concerning the specified ASNs",
	Long:  ``,
	Run: func(cmd *cobra.Command, args []string) {
		CommandProvided = true
		IntervalEnabled = true
	},
}

func init() {
	rootCmd.AddCommand(activeCmd)

	// Add an integer flag named "interval" with shorthand "i" and default value of 10
	activeCmd.Flags().Int64Var(&Interval, "interval", 10, "Interval for hijack detection in seconds")
	activeCmd.Flags().Int64Var(&Asn, "asn", -1, "AS number to mitigate the hijack for")
	activeCmd.Flags().StringVar(&PipeName, "pipename", "", "Named pipe file to write the mitigation commands to")
}
