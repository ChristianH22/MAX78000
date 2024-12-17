#ifndef VECTOR_UTILS_H
#define VECTOR_UTILS_H

#include <stdint.h>
#include <stddef.h>

#define VECTOR_SIZE 16384 
#define MAX_FILES 100  // Example
#define MAX_FILENAME_LENGTH 256
extern char file_names[MAX_FILES][MAX_FILENAME_LENGTH];
extern int file_count;
extern int mounted;

extern int16_t voiceVector[VECTOR_SIZE];
size_t read_vector_from_binary(const char *filename, int16_t *voiceVector);
int listFilesInBinDir();

int readAllFilesInBinDir(char *file_name);
#endif /* VECTOR_UTILS_H */