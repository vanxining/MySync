package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"os"
)

var basePathPtr *string

// FileChangedEvent represents a file changed event occurred remotely.
type FileChangedEvent struct {
	Tag  string `json:"tag"`
	Path string `json:"sourcePath"`
	Data string `json:"data"`
}

func handleEvents(event *FileChangedEvent) {
	log.Printf("%s %s (%d bytes)", event.Tag, event.Path, len(event.Data))

	var err error

	switch event.Tag {
	case "NEW", "MOD":
		err = ioutil.WriteFile(event.Path, []byte(event.Data), 0644)
	case "MOV":
		err = os.Rename(event.Path, event.Data)
	case "DEL":
		err = os.Remove(event.Path)
	default:
		log.Printf("Unrecognized file changed event")
		return
	}

	if err != nil {
		log.Print(err)
	}
}

func handler(w http.ResponseWriter, r *http.Request) {
	var event FileChangedEvent

	decoder := json.NewDecoder(r.Body)
	err := decoder.Decode(&event)
	if err != nil {
		log.Printf("Illege JSON data: %v", err)

		w.WriteHeader(http.StatusUnprocessableEntity)
		return
	}
	defer r.Body.Close()

	handleEvents(&event)
}

func main() {
	basePathPtr = flag.String("path", ".", "the path to the directory to sync")
	portPtr := flag.Int("port", 58667, "the remote port")

	http.HandleFunc("/", handler)

	fmt.Printf("Serving on port %d...\n", *portPtr)
	http.ListenAndServe(fmt.Sprintf(":%d", *portPtr), nil)
}