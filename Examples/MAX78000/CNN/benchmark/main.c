#include "board.h"
#include "cli.h"
#include "nvic_table.h"
#include "sdhc.h"
#include "uart.h"
#include "user-cli.h"

#ifdef BOARD_EVKIT_V1
#warning This example is not supported by the MAX78000EVKIT.
#endif

/******************************************************************************/
int main(void)
{
    int err;
    printf("\n\n***** MAX78000 CLI SYSTEM : Jeffrey Barahona & Christian Hoimes *****\n");

    // Wait for SD Card to be inserted
    waitCardInserted();

    printf("Card inserted.\n");
    while (MXC_UART_GetActive(MXC_UART_GET_UART(CONSOLE_UART))) {}

    // Initialize CLI
    if ((err = MXC_CLI_Init(MXC_UART_GET_UART(CONSOLE_UART), user_commands, num_user_commands)) !=
        E_NO_ERROR) {
        return err;
    }

    // Run CLI
    while (1) {}
}