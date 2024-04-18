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
var active = &cobra.Command{
	Use:   "active",
	Short: "Detect Hijacks for a specific AS and mitigate them in real-time",
	Long:  ``,
	Run: func(cmd *cobra.Command, args []string) {
		CommandProvided = true
		SpecificAsn = true
	},
}

func init() {
	rootCmd.AddCommand(active)

	rootCmd.PersistentFlags().Int64VarP(&Interval, "interval", "i", -1, "The interval in minutes to check for hijacks")
	rootCmd.PersistentFlags().StringVar(&MitigationScriptPath, "mitigation_script_path", "", "The interval in minutes to check for hijacks")
}
