#include <stdint.h>
#include <string.h>

#define DTC_BLOCK_LEN 256
#define CODE_FLASH_START 0x00001000
#define CODE_FLASH_SIZE 0x1000

// CRC32 lookup table
static const uint32_t crc32_table[256] = {
    0x00000000, 0x77073096, 0xee0e612c, 0x990951ba, 0x076dc419, 0x706af48f, 0xe963a535, 0x9e6495a3,
    0x0edb8832, 0x79dcb8a4, 0xe0d5e91e, 0x97d2d988, 0x09b64c2b, 0x7eb17cbd, 0xe7b82d07, 0x90bf1d91,
    // ... (完整CRC32表)
};

/**
 * @brief Calculate CRC32 checksum
 * @param data Pointer to data
 * @param length Length of data
 * @return CRC32 checksum
 */
static uint32_t calculate_crc32(const uint8_t *data, size_t length)
{
    uint32_t crc = 0xFFFFFFFF;
    for (size_t i = 0; i < length; i++) {
        crc = (crc >> 8) ^ crc32_table[(crc ^ data[i]) & 0xFF];
    }
    return ~crc;
}

typedef struct 
{ 
    unsigned int block_id; /**< Unique identifier for the DTC block. */ 
    unsigned char block_data[DTC_BLOCK_LEN]; /**< Data stored in the DTC block. */ 
    unsigned char ATAC_Cfg[8]; /**< Enable Condition of ATAC, size is 8 bytes */ 
    unsigned char ARM_STATUS[8]; 
    unsigned int checksum; /**< CRC32 checksum for data integrity verification. */ 
} dtc_block_t;

/**
 * @brief Read ATAC_Cfg data from code flash
 * @param data Pointer to store read data
 * @param len Length of data to read (max 8 bytes)
 * @return 0 on success, 1 on error
 */
uint8_t Read_ATAC_Cfg(uint8_t *data, uint16_t len)
{
    if (len > 8 || data == NULL) return 1;
    
    dtc_block_t *flash_ptr = (dtc_block_t *)CODE_FLASH_START;
    
    // Search for the current block in code flash
    for (uint32_t i = 0; i < CODE_FLASH_SIZE/sizeof(dtc_block_t); i++) {
        if (flash_ptr->block_id != 0xFFFFFFFF) { // Valid block
            memcpy(data, flash_ptr->ATAC_Cfg, len);
            return 0;
        }
        flash_ptr++;
    }
    
    return 1; // Block not found
}

/**
 * @brief Write ATAC_Cfg data to code flash
 * @param data Pointer to data to write
 * @param size Size of data to write (max 8 bytes)
 * @return 0 on success, 1 on error
 */
uint8_t Write_ATAC_Cfg(uint8_t *data, uint32_t size)
{
    if (size > 8 || data == NULL) return 1;
    
    dtc_block_t *flash_ptr = (dtc_block_t *)CODE_FLASH_START;
    
    // Find first empty block or overwrite existing
    for (uint32_t i = 0; i < CODE_FLASH_SIZE/sizeof(dtc_block_t); i++) {
        if (flash_ptr->block_id == 0xFFFFFFFF || 
            flash_ptr->block_id == 0x00000000) { // Empty or default block
            
            // Update block data
            flash_ptr->block_id = 0x00000000; // Default ID
            memcpy(flash_ptr->ATAC_Cfg, data, size);
            
            // Calculate CRC32 checksum for the block
            flash_ptr->checksum = calculate_crc32((uint8_t *)flash_ptr, sizeof(dtc_block_t) - sizeof(unsigned int));
            
            return 0;
        }
        flash_ptr++;
    }
    
    // No space available, erase entire flash
    memset((void *)CODE_FLASH_START, 0xFF, CODE_FLASH_SIZE);
    
    // Write to first block after erase
    flash_ptr = (dtc_block_t *)CODE_FLASH_START;
    flash_ptr->block_id = 0x00000000;
    memcpy(flash_ptr->ATAC_Cfg, data, size);
    
    // Calculate CRC32 checksum for the first block
    flash_ptr->checksum = calculate_crc32((uint8_t *)flash_ptr, sizeof(dtc_block_t) - sizeof(unsigned int));
    
    // Initialize remaining blocks with default values and calculate checksums
    for (uint32_t i = 1; i < CODE_FLASH_SIZE/sizeof(dtc_block_t); i++) {
        flash_ptr++;
        flash_ptr->block_id = 0xFFFFFFFF;
        flash_ptr->checksum = calculate_crc32((uint8_t *)flash_ptr, sizeof(dtc_block_t) - sizeof(unsigned int));
    }
    
    return 0;
}