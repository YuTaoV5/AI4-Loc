/* SPDX-License-Identifier: GPL-2.0 */
/* Guest-only workload. Never executed on the host. Retain and fault in memory. */
#include <stdlib.h>
#include <unistd.h>
int main(void)
{
    void *blocks[1024];
    for (unsigned i=0; i<1024; ++i) {
        blocks[i]=malloc(8*1024*1024);
        if (!blocks[i]) { sleep(1); --i; continue; }
        volatile unsigned char *p=blocks[i];
        for (unsigned j=0; j<8*1024*1024; j+=4096) p[j]=1;
    }
    sleep(60);
    return 0;
}
