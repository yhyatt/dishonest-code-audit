// Synthetic fixture — intentionally contains stub patterns for the audit harness.

package main

import (
	"net/http"
)

func chargeHandler(w http.ResponseWriter, r *http.Request) {
	// HIGH: handler panics with "not implemented" in a user-reachable path.
	panic("not implemented")
}

func main() {
	http.HandleFunc("/charge", chargeHandler)
	_ = http.ListenAndServe(":8080", nil)
}
