#include "read_bin.h"
#include "sdhc.h"
#include "ff.h"
#include <stdio.h>
#include <stdlib.h>
#include "inference.h"
#define VECTOR_SIZE 16384 

extern char file_names[MAX_FILES][MAX_FILENAME_LENGTH];
extern int file_count;
extern int mounted; 

int16_t voiceVector[VECTOR_SIZE];

size_t read_vector_from_binary(const char *filename, int16_t *voiceVector) 
{
    
    FIL file; 
    FRESULT result; 
    UINT bytesRead = 0;
    DIR dir;
    FILINFO fno;
    listFilesInBinDir();


    
    if (voiceVector == NULL) {
        perror("Invalid memory pointer for voiceVector");
        return 0;
    }
    if (!mounted) {
        if (mount() != FR_OK) {
            printf("Error mounting SD card.\n");
            return 0;
        }
    }
    //printf("%s", filename);

    // Opens SD Card
    result = f_open(&file, filename, FA_READ);
    if (result != FR_OK) {
        printf("Error opening file: %d\n", result);
        return 0;
    }
    result = f_read(&file, voiceVector, sizeof(int16_t) * VECTOR_SIZE, &bytesRead);
    if (result != FR_OK) {
        printf("Error reading file: %d\n", result);
        //printf("%s", filename);
        f_close(&file);
        return 0;
    }

    if (bytesRead != sizeof(int16_t) * VECTOR_SIZE) {
        printf("Error: Not enough data read from file. Expected %zu bytes, got %u bytes\n",
               sizeof(int16_t) * VECTOR_SIZE, bytesRead);
        f_close(&file);
        return 0;
    }

    f_close(&file);


    return bytesRead / sizeof(int16_t);
}



int listFilesInBinDir()
{

    FRESULT err;   
    DIR dir;   
    FILINFO fno;

    
    if (!mounted) {
        if (mount() != FR_OK) {
            printf("Error mounting SD card.\n");
            return -1;
        }
    }

    if (cd("/bin/") != FR_OK) {
        printf("Error changing to 'bin' directory.\n");
        return -1;
    }

    if ((err = f_opendir(&dir, "/bin/")) != FR_OK) {
        printf("Error opening 'bin' directory");
        return err;
    }
    file_count = 0;
    while (1) {
        err = f_readdir(&dir, &fno);
        if (err != FR_OK || fno.fname[0] == 0) {
            break; 
        }
        if (!(fno.fattrib & AM_DIR)) {
            if (file_count < MAX_FILES) {
                snprintf(file_names[file_count], MAX_FILENAME_LENGTH, "%s", fno.fname);
                file_count++;
            } else {
                printf("File list is full. Only %d files listed.\n", MAX_FILES);
                break;
            }
        }
    }
    //f_closedir(&dir);

    // printf("Found %d files in 'bin' directory.\n", file_count);
    // for (int i = 0; i < file_count; i++) {
    //     printf("File %d: %s\n", i + 1, file_names[i]);
    // }

    return FR_OK;
}


int readAllFilesInBinDir(char *file_name) {
    if (listFilesInBinDir() != FR_OK) {
        printf("Failed to list files in 'bin' directory.\n");
        return 0;
    }

    if (strcmp(file_name, "all") == 0){
        for (int i = 0; i < file_count; i++) {
        
            //printf("Reading file %s...\n", file_names[i]);

            size_t elementsRead = read_vector_from_binary(file_names[i], voiceVector);
            run_inference(file_names[i]);
            // if (elementsRead > 0) {
            //     printf("Successfully read %zu elements from %s\n", elementsRead, file_names[i]);
            // } else {
            //     printf("Failed to read elements from %s\n", file_names[i]);
            // }
        

        }
    } else {
        for (int i = 0; i < file_count; i++) {
        
            //printf("Reading file %s...\n", file_names[i]);
            if (strcmp(file_names[i], file_name) == 0) {
                size_t elementsRead = read_vector_from_binary(file_names[i], voiceVector);
                run_inference(file_names[i]);
                // if (elementsRead > 0) {
                //     printf("Successfully read %zu elements from %s\n", elementsRead, file_names[i]);
                // } else {
                //     printf("Failed to read elements from %s\n", file_names[i]);
                // }
            }
        }
    }
    return 0;
}

/*
char **listFilesInBinDir(int *fileCount) {
    FRESULT err;   // FATFS result code
    DIR dir;       // Directory object
    FILINFO fno;
    char **fileArray;
    int count = 0;
    
    // Initialize fileCount
    if (fileCount == NULL) {
        printf("Invalid fileCount pointer.\n");
        return NULL;
    }
    *fileCount = 0;

    // Check if SD card is mounted
    if (!mounted) {
        if (mount() != FR_OK) {
            printf("Error mounting SD card.\n");
            return NULL;
        }
    }

    // Change to "bin" directory
    if (cd("/bin/") != FR_OK) {
        printf("Erro to 'bin' directory.\n");
        return NULL;
    }

    // Initialize directory object
    if ((err = f_opendir(&dir, "/bin/")) != FR_OK) {
        printf("Error opening 'bin' directory.\n");
        return NULL;
    }

    // Allocate initial space for file array
    fileArray = malloc(MAX_FILES * sizeof(char *));
    if (fileArray == NULL) {
        printf("Error allocating memory for file list.\n");
        f_closedir(&dir);
        return NULL;
    }

    // Loop through directory entries
    while (1) {
        err = f_readdir(&dir, &fno);
        if (err != FR_OK || fno.fname[0] == 0) {
            break; // Exit loop if end of directory or error
        }

        // Check if the entry is a file (not a directory)
        if (!(fno.fattrib & AM_DIR)) {
            if (count < MAX_FILES) {
                fileArray[count] = malloc(MAX_FILENAME_LENGTH);
                if (fileArray[count] == NULL) {
                    printf("Error allocating memory for file name.\n");
                    break;
                }
                snprintf(fileArray[count], MAX_FILENAME_LENGTH, "%s", fno.fname);
                count++;
            } else {
                printf("File list is full. Only %d files listed.\n", MAX_FILES);
                break;
            }
        }
    }

    // Close directory
    f_closedir(&dir);

    // Set fileCount to the number of files found
    *fileCount = count;

    printf("Found %d files in 'bin' directory.\n", count);
    for (int i = 0; i < count; i++) {
        printf("File %d: %s\n", i + 1, fileArray[i]);
    }

    return fileArray;
}


void freeFileArray(char **fileArray, int fileCount) {
    if (fileArray == NULL) return;
    for (int i = 0; i < fileCount; i++) {
        free(fileArray[i]);
    }
    free(fileArray);
}
*/






/*


#include "read_bin.h"
#include "sdhc.h"
#include "ff.h"
#include <stdio.h>
#include <stdlib.h>



size_t read_vector_from_binary(const char *filename, int16_t *voiceVector) 
{
    FILE *file;
    file = fopen(filename, "rb");
    if (file == NULL) {
        perror("Error opening file****");
        return 0;
    }
    if (voiceVector == NULL) {
        perror("Can't allocate memory properly");
        fclose(file);
        return 0;
    }
    size_t elements_read = fread(voiceVector, sizeof(int16_t), VECTOR_SIZE, file);
    if (elements_read != VECTOR_SIZE) {
        perror("Must be 16384 bits");
        fclose(file);
        return 0;
    }
    fclose(file);

    return elements_read;
}
*/