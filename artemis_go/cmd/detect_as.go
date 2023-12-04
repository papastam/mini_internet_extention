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

// detectCmd represents the detect command
var detect_asCmd = &cobra.Command{
	Use:   "detect_as",
	Short: "Detect all hijacks for a specified ASn",
	Long:  ``,
	Run: func(cmd *cobra.Command, args []string) {
		CommandProvided = true
		SpecificAsn = true
	},
}

func init() {
	rootCmd.AddCommand(detect_asCmd)

	rootCmd.PersistentFlags().Int64VarP(&Asn, "asn", "a", 0, "The ASN to detect hijacks for")
	rootCmd.PersistentFlags().StringVar(&InputType, "input_type", "file", "Declare the type of input (file or directory)")

}
