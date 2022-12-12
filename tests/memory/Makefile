
.PHONY: all install download clean

BUILT_FILES= threaded_memtest

FILES=threaded_memtest.c memory.py

run: $(FILES) build

build: $(BUILT_FILES)


# test-specific rules:
CFLAGS+=-Wall
ARCH := $(shell uname -i)
ifeq ($(ARCH),ppc64)
CFLAGS+=-m64
endif

threaded_memtest: threaded_memtest.c
	$(CC) $(CFLAGS) -lpthread $< -o $@


