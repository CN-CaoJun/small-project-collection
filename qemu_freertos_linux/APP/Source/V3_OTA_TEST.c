#include "stdio.h"
#include "V3_OTA_TEST.h"



uint8_t LeaveUpdateMode_Sts = 0xFF;
uint8_t LeaveUpdateMode_Sent_Flag = 0xFF;
boolean LeaveUpdateMode_Send_Control = FALSE;



void OTA_message_enter(void)
{
    LeaveUpdateMode_Sts = 0x01;
    LeaveUpdateMode_Send_Control = TRUE;

    printf("HISIP recevie LeaveUpdateMode_Sts : %d, set LeaveUpdateMode_Send_Control: %d \r\n",LeaveUpdateMode_Sts, LeaveUpdateMode_Send_Control);
}


void OTA_message_leave(void)
{
    LeaveUpdateMode_Sts = 0x02;
    LeaveUpdateMode_Send_Control = TRUE;

    printf("HISIP recevie LeaveUpdateMode_Sts : %d, set LeaveUpdateMode_Send_Control: %d \r\n",LeaveUpdateMode_Sts, LeaveUpdateMode_Send_Control);
}




void OTA_LeavemodeSts_Send(void)
{
	static uint32_t sent_count = 0u;
    static boolean sent_complete = FALSE;

	if(TRUE == LeaveUpdateMode_Send_Control)
    {
        if( sent_count < 0x05)
        {
            // IPC_TX_SIG_MSG33B_HUT17_OTA_OTASTS(LeaveUpdateMode_Sts);
            printf("Send KBCM LeaveUpdateMode_Sts = 0x%02x \r\n", LeaveUpdateMode_Sts);
            sent_count++;
            if (sent_count == 5)
            {
                printf("Sent 5 times LUPMS\r\n");
            }
        }
        else if ((sent_count >= 5) && (sent_count < 10))
        {
            //IPC_TX_SIG_MSG33B_HUT17_OTA_OTASTS(0x00);
           printf("Send KBCM LeaveUpdateMode_Sts = 0x00 \r\n");

            sent_count ++;

            if (sent_count == 10)
            {
                sent_complete = TRUE;
                printf("Sent 5 times 0x00\r\n");

            }
        }   
        else
        {    
            if( sent_complete == TRUE)
            {
                LeaveUpdateMode_Sent_Flag = 0x00;

                //VIP_Queue_Message(VIPq_SwUpd_Rep_OTA_EnterExit_LeaveUpdateMode, COVER);
                printf("send HISIP 	LeaveUpdateMode_Sent_Flag = %d LeaveUpdateMode_Sts = %d \r\n", LeaveUpdateMode_Sent_Flag,LeaveUpdateMode_Sts);
                sent_complete = FALSE;

                printf("Inform OTA moudle that LUPMS\r\n");
            }
            else
            {
                LeaveUpdateMode_Sent_Flag = 0x01;

            }
        
            LeaveUpdateMode_Send_Control = FALSE;
            sent_count = 0;
        }        
    }
    else
    {
      printf("No action\r\n");
    }

}
