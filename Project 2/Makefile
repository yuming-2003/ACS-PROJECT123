CC ?= gcc
CFLAGS ?= -O3 -march=native -ffast-math -fopenmp -Wall -Wextra
LDFLAGS ?=

BIN_DIR := bin
SRC_DIR := src

MICROBENCH := $(BIN_DIR)/microbench

all: $(MICROBENCH)

$(BIN_DIR):
	mkdir -p $(BIN_DIR)

$(MICROBENCH): | $(BIN_DIR)
	$(CC) $(CFLAGS) $(SRC_DIR)/microbench.c -o $(MICROBENCH) $(LDFLAGS)

clean:
	rm -rf $(BIN_DIR)

.PHONY: all clean
