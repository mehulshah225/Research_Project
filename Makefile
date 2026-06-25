CC = gcc
CFLAGS = -O3

TARGETS = esop_min maslov

all: $(TARGETS)

esop_min: main_code/esop_min.c
	$(CC) $(CFLAGS) main_code/esop_min.c -o esop_min

maslov: maslov_calculator/maslov.c
	$(CC) $(CFLAGS) maslov_calculator/maslov.c -o maslov

clean:
	rm -f $(TARGETS)
