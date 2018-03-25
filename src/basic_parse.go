package main

import (
	"bytes"
	"fmt"
	"reflect"

	"gopkg.in/bblfsh/client-go.v2"
	"gopkg.in/bblfsh/client-go.v2/tools"
	"gopkg.in/bblfsh/sdk.v1/uast"
)

func printTokens(n *uast.Node) {
	fmt.Println(n.Token)

	for _, c := range n.Children {
		printTokens(c)
	}
}

func main() {
	client, err := bblfsh.NewClient("localhost:9432")
	if err != nil {
		panic(err)
	}

	res, err := client.NewParseRequest().ReadFile("/home/hydra/projects/source_d/data/dummy.py").Do()
	if err != nil {
		panic(err)
	}
	if reflect.TypeOf(res.UAST).Name() != "Node" {
		fmt.Errorf("Node must be the root of a UAST")
	}

	// fmt.Println("Iterating the UAST...")
	// iter, err := tools.NewIterator(res.UAST, tools.PreOrder)
	// defer iter.Dispose()
	// for n := range iter.Iterate() {
	// 	fmt.Println(n)
	// }

	root := res.UAST
	fmt.Println(root.Children[0].InternalType)
	for _, n := range root.Children[0].Children {
		fmt.Printf("%v := {%v || %v}\n", n.InternalType, n.Properties, n.Roles)

	}

	fmt.Println("Printing tokens.")
	printTokens(res.UAST)

	fmt.Println("Pretty writing tokens.")
	buf := bytes.NewBuffer(nil)
	// uast.IncludeFlag = {uast}
	IncludeCustom := uast.IncludeChildren |
		uast.IncludeProperties |
		uast.IncludeInternalType
		// uast.IncludeTokens |
	uast.Pretty(res.UAST, buf, IncludeCustom)
	fmt.Printf("Buffer %v", buf)
	// query := "//*[@roleIdentifier and not(@roleQualified)]"
	// nodes, _ := tools.Filter(res.UAST, query)
	// for _, n := range nodes {
	// 	fmt.Println(n)
	// }

	strres, err := tools.FilterString(res.UAST, "name")
	fmt.Printf("Str result: %v\n", strres)

	query := "//*[@InternalType]"
	nodes, _ := tools.Filter(res.UAST, query)
	for _, n := range nodes {
		fmt.Println(n)
	}
}
