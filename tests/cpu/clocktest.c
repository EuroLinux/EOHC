/* clocktest.c - check for clock jitter on SMP machines */

#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#include <sys/time.h>

#define __USE_GNU 1
#include <sched.h>

#define NSEC_PER_SEC    1000000000
#define MAX_AVE_JITTER      (double)0.2
#define MAX_ADJ_JITTER      (double)0.2
#define ITERATIONS      10000
//#define ITERATIONS      1

#define NSEC(ts) (ts.tv_sec*NSEC_PER_SEC + ts.tv_nsec)

#ifdef OLD_SCHED_SETAFFINITY
#define setaffinity(mask) sched_setaffinity(0,mask)
#else
#ifdef CPU_ALLOC
#define setaffinity(mask) sched_setaffinity(0,conf_cpus_size, mask)
#else
#define setaffinity(mask) sched_setaffinity(0,sizeof(cpu_set_t),mask)
#endif
#endif


size_t conf_cpus_size;

#ifdef CPU_ALLOC
cpu_set_t* cpu_alloc(unsigned num_cpus){
    cpu_set_t *ret;
    printf("using CPU_CALLOC with num_cpus = %d\n", num_cpus);
    ret = CPU_ALLOC(num_cpus);
    if (ret)
       conf_cpus_size = CPU_ALLOC_SIZE(num_cpus);
    return ret;
}

#define cpu_zero(cpumask) CPU_ZERO_S(conf_cpus_size, cpumask)
#define cpu_set(cpu,cpumask) CPU_SET_S(cpu, conf_cpus_size, cpumask)
#else
cpu_set_t* cpu_alloc(unsigned num_cpus){
	return malloc(sizeof(cpu_set_t));
}
#define cpu_zero(cpumask) CPU_ZERO(cpumask)
#define cpu_set(cpu,cpumask) CPU_SET(cpu,cpumask)
#endif

int test_clock_jitter(){
    cpu_set_t* cpumask;
    struct timespec *time;
    unsigned long total, maxDelta;
    long delta;
    double largest_jitter = 0.0, ave_jitter=0.0, jitter=0.0;
    unsigned cpu, num_cpus, iter, conf_cpus;
    int failures = 0, found;
    unsigned last;

    conf_cpus = sysconf(_SC_NPROCESSORS_CONF);
    num_cpus = sysconf(_SC_NPROCESSORS_ONLN);
    if (num_cpus != conf_cpus){
       	printf("Warning: %u cpus are online, but %u cpus are configured.\n",
	       num_cpus, conf_cpus);
    }
    if (num_cpus == 1) {
        printf("Single CPU detected. No clock jitter testing necessary.\n");
        return 0;
    }

    printf ("Testing for clock jitter on %u cpus\n", num_cpus);

    time=malloc(conf_cpus * sizeof(struct timespec));
    cpumask = cpu_alloc(conf_cpus);
    if (!cpumask) {
	    printf("cpu malloc failed\n");
	    return -1;
    }

    for (iter=0; iter<ITERATIONS; iter++){
        for (cpu=0; cpu < conf_cpus; cpu++) {
            cpu_zero(cpumask); cpu_set(cpu,cpumask);
            if (setaffinity(cpumask) == -1){
                time[cpu].tv_sec = 0;
                time[cpu].tv_nsec = 0;
                continue;
    	    }
    	    /*
    	     * by yielding this process should get scheduled on the cpu
        	 * specified by setaffinity
	         */
        	sched_yield();
            if (clock_gettime(CLOCK_REALTIME, &time[cpu]) < 0) {
                perror("clock_gettime"); return 1;
            }
        }
        total = 0;
	delta = maxDelta = 0;
	last = 0;
	for (cpu=1; cpu < conf_cpus; cpu++) {
		if (NSEC(time[cpu]) == 0)
			continue;
		found = 0;
		for (last = cpu - 1; last > 0; last--) {
			if (NSEC(time[last])) {
				found = 1;
				break;
			}
		}
		if (!found)
			continue;

    		delta =  NSEC(time[cpu]) - NSEC(time[last]);
    		if (delta > maxDelta)
    			maxDelta = delta;
    		total += abs(delta);
	}
	ave_jitter = ((double)total)/(((double)num_cpus-1)*(double)NSEC_PER_SEC);
#ifdef DEBUG
        printf("DEBUG: average jitter for pass %u was %f, max adjacent %f\n",
		iter, ave_jitter, (double)maxDelta/(double)NSEC_PER_SEC);
#endif

	if (ave_jitter > MAX_AVE_JITTER){
	        printf ("ERROR, average jitter = %f sec/cpu\n",ave_jitter);
	        printf ("iter = %u\n",iter);
            failures++;
    	}
	jitter = (double)maxDelta/(double)NSEC_PER_SEC;
	if (jitter > MAX_ADJ_JITTER){
	        printf ("ERROR, maximum adjacent jitter = %f\n",jitter);
	        printf ("iter = %u\n",iter);
            failures++;
    	}

	if (ave_jitter > largest_jitter)
	    largest_jitter = ave_jitter;
    }

    if (failures == 0)
        printf ("PASSED, largest jitter seen was %lf\n",largest_jitter);
    else {
        printf ("FAILED, %u iterations failed\n",failures);
        printf ("largest jitter seen was %lf\n",largest_jitter);
    }

    return (failures > 0);
}

int test_clock_direction()
{
	time_t starttime = 0;
	time_t stoptime = 0;
	int sleeptime = 60;
	int delta = 0;

	time(&starttime);
	sleep(sleeptime);
	time(&stoptime);

	delta = (int)stoptime - (int)starttime - sleeptime;
	printf("clock direction test: start time %d, stop time %d, sleeptime %u, delta %u\n",
				(int)starttime, (int)stoptime, sleeptime, delta);
	if (delta != 0)
	{
		printf("FAILED\n");
		return 1;
	}
	/* otherwise */
	printf("PASSED\n");
	return 0;
}


int main()
{
	int failures = test_clock_jitter();
	if (failures == 0)
	{
		failures = test_clock_direction();
	}
	return failures > 0;
}
