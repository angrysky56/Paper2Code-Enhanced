.PHONY: build test lint install clean

build:
	go build -o bin/paper2code-pp-cli ./cmd/paper2code-pp-cli

test:
	go test ./...

lint:
	golangci-lint run

install:
	go install ./cmd/paper2code-pp-cli

clean:
	rm -rf bin/

build-mcp:
	go build -o bin/paper2code-pp-mcp ./cmd/paper2code-pp-mcp

install-mcp:
	go install ./cmd/paper2code-pp-mcp

build-all: build build-mcp
