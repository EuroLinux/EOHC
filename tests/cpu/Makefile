
.PHONY: all install download clean

BUILT_FILES= clocktest
FILES=clocktest.c 

build: $(BUILT_FILES)

CFLAGS+=-Wall
CFLAGS+=-DCPU_ALLOC
# sched_setaffinity has no size_t argument on older systems.
ifeq ($(shell grep 'sched_setaffinity.*size_t' /usr/include/sched.h),)
CFLAGS+=-DOLD_SCHED_SETAFFINITY
endif

clocktest: clocktest.c
	$(CC) $(CFLAGS) -lrt $< -o $@
