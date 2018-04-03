package main

import (
	"fmt"
	"os"
	"path/filepath"
	"reflect"

	"gopkg.in/bblfsh/client-go.v2"
	"gopkg.in/bblfsh/sdk.v1/uast"
)

type Rule struct {
	consequent  *uast.Node
	antecedents []*uast.Node
}

func filesList(searchDir string) ([]string, error) {

	fileList := []string{}
	err := filepath.Walk(searchDir, func(path string, f os.FileInfo, err error) error {
		fileList = append(fileList, path)
		return nil
	})

	for _, file := range fileList {
		fmt.Println(file)
	}

	return fileList, err
}

func printTokens(n *uast.Node) {
	fmt.Println(n.Token)

	for _, c := range n.Children {
		printTokens(c)
	}
}

func writeNode(n *uast.Node, flags uast.IncludeFlag) {
	fmt.Printf("%v", n.InternalType)
	if flags.Is(uast.IncludeProperties) {
		fmt.Printf(" [%v]", n.Properties)
	}
	// if len(options) > 2 {
	// 	fmt.Printf(" [%v]", n.Properties)
	// }
}

func writeNodes(n *uast.Node, flags uast.IncludeFlag) {
	if len(n.Children) > 0 {
		writeNode(n, flags)

		fmt.Printf(" -> ")

		for i, node := range n.Children {
			if i > 0 {
				fmt.Printf(",")
			}
			writeNode(node, flags)
		}
		fmt.Println()

		for _, node := range n.Children {
			writeNodes(node, flags)
		}
	}
}

func getRule(n *uast.Node) Rule {
	rule := Rule{n, n.Children}
	return rule
}

func getRules(n *uast.Node) []Rule {
	var rules []Rule
	if len(n.Children) > 0 {
		rules = append(rules, getRule(n))

		for _, node := range n.Children {
			rules = append(rules, getRules(node)...)
		}
	}
	return rules
}

func printRules(rules []Rule, flags uast.IncludeFlag) {
	for _, rule := range rules {

		for i, node := range rule.antecedents {
			if i > 0 {
				fmt.Printf(",")
			}
			fmt.Printf("%v", node.InternalType)
			if flags.Is(uast.IncludeProperties) {
				fmt.Printf("[%v]", node.Properties)
			}
		}
		fmt.Printf("->")
		fmt.Printf("%v", rule.consequent.InternalType)
		if flags.Is(uast.IncludeProperties) {
			fmt.Printf("[%v]\n", rule.consequent.Properties)
		}
	}
}

func main() {
	client, err := bblfsh.NewClient("localhost:9432")
	if err != nil {
		panic(err)
	}

	files, err := filesList("/home/hydra/repos/framework/")
	for _, file := range files {
		// res, err := client.NewParseRequest().ReadFile("/home/hydra/projects/source_d/data/dummy.py").Do()
		res, err := client.NewParseRequest().ReadFile(file).Do()
		if err != nil {
			panic(err)
		}
		if reflect.TypeOf(res.UAST).Name() != "Node" {
			fmt.Errorf("Node must be the root of a UAST")
		}
		IncludeCustom := uast.IncludeChildren |
			uast.IncludeProperties |
			uast.IncludeInternalType

		var rules []Rule
		rules = getRules(res.UAST)

		fmt.Println("Printing parsed rules")
		printRules(rules, IncludeCustom)
	}

	// fmt.Println("Iterating the UAST...")
	// iter, err := tools.NewIterator(res.UAST, tools.PreOrder)
	// defer iter.Dispose()
	// for n := range iter.Iterate() {
	// 	fmt.Println(n)
	// }

	//
	// root := res.UAST
	// fmt.Println(root.Children[0].InternalType)
	// for _, n := range root.Children[0].Children {
	// 	fmt.Printf("%v := {%v || %v}\n", n.InternalType, n.Properties, n.Roles)
	// }

	// fmt.Println("Printing tokens.")
	// printTokens(res.UAST)
	//
	// fmt.Println("Pretty writing tokens.")
	// buf := bytes.NewBuffer(nil)
	// // uast.IncludeFlag = {uast}
	// IncludeCustom := uast.IncludeChildren |
	// 	uast.IncludeProperties |
	// 	uast.IncludeInternalType
	// 	// uast.IncludeTokens |
	// uast.Pretty(res.UAST, buf, IncludeCustom)
	// fmt.Printf("Buffer %v", buf)
	// // query := "//*[@roleIdentifier and not(@roleQualified)]"
	// // nodes, _ := tools.Filter(res.UAST, query)
	// // for _, n := range nodes {
	// // 	fmt.Println(n)
	// // }
	//
	// strres, err := tools.FilterString(res.UAST, "name")
	// fmt.Printf("Str result: %v\n", strres)
	//
	// query := "//*[@InternalType]"
	// nodes, _ := tools.Filter(res.UAST, query)
	// for _, n := range nodes {
	// 	fmt.Println(n)
	// }
	//
	// fmt.Println("Basic rules")
	// writeRule(res.UAST, uast.IncludeChildren)
	//
	// fmt.Printf("\nExtended rules")
	// writeRule(res.UAST, uast.IncludeProperties)
}
