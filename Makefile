CC = gcc
CFLAGS = -O3 -Wall

SRC_DIR = main_code

ESOP_SRC = \
	$(SRC_DIR)/main.c \
	$(SRC_DIR)/cube_containment.c \
	$(SRC_DIR)/cube_merge.c

ESOP_HDR = \
	$(SRC_DIR)/cube_containment.h \
	$(SRC_DIR)/cube_merge.h \
	$(SRC_DIR)/cube_types.h

all: esop_min maslov

# -------------------------
# Build ESOP optimizer
# -------------------------
esop_min: $(ESOP_SRC) $(ESOP_HDR)
	$(CC) $(CFLAGS) $(ESOP_SRC) -o esop_min

# -------------------------
# Build Maslov cost model
# -------------------------
maslov:
	$(CC) $(CFLAGS) maslovCalculator/maslovCalculator.c -o maslov

# -------------------------
# Clean
# -------------------------
clean:
	rm -f esop_min maslov
