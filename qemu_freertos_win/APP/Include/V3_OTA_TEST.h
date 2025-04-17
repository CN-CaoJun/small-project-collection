#ifndef V3_OTA_TEST_H
#define V3_OTA_TEST_H

typedef unsigned char boolean;

#ifndef FALSE
#define FALSE 0
#endif

#ifndef TRUE
#define TRUE 1
#endif

extern uint8_t LeaveUpdateMode_Sts;
extern uint8_t LeaveUpdateMode_Sent_Flag;
extern boolean LeaveUpdateMode_Send_Control;


extern void OTA_message_enter(void);
extern void OTA_message_leave(void);
extern void OTA_LeavemodeSts_Send(void);
#endif