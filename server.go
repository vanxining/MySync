package main

import (
	"compress/gzip"
	"encoding/json"
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"runtime"
	"strings"
)

var basePathPtr *string

func byteCount(b int64) string {
	const unit = 1024
	if b < unit {
		return fmt.Sprintf("%d B", b)
	}
	div, exp := int64(unit), 0
	for n := b / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %ciB",
		float64(b)/float64(div), "KMGTPE"[exp])
}

// FileChangedEvent represents a file changed event occurred remotely.
type FileChangedEvent struct {
	Tag  string `json:"tag"`
	Path string `json:"sourcePath"`
	Data string `json:"data"`
}

func handleEvents(event *FileChangedEvent) {
	if runtime.GOOS != "windows" {
		event.Path = strings.ReplaceAll(event.Path, `\`, "/")
		if event.Tag == "MOV" {
			event.Data = strings.ReplaceAll(event.Data, `\`, "/")
		} else {
			event.Data = strings.ReplaceAll(event.Data, "\r\n", "\n")
		}
	}

	log.Printf("%s %s (%s)", event.Tag, event.Path, byteCount(int64(len(event.Data))))

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

	decompressor, err := gzip.NewReader(r.Body)
	if err != nil {
		log.Printf("Illege Gzip data: %v", err)

		w.WriteHeader(http.StatusUnprocessableEntity)
		return
	}
	defer decompressor.Close()

	decoder := json.NewDecoder(decompressor)
	err = decoder.Decode(&event)
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
