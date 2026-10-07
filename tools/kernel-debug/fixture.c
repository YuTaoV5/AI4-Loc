__attribute__((noinline)) int crash_site(int *values, int index) {
    return values[index];
}
int entry(void) { int values[2] = {7, 9}; return crash_site(values, 1); }
