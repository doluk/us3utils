#pragma description AUC .mwrs file
#pragma author Doluk
#pragma MIME application/mwrs

struct MWRS {
    be u8 cell;
    char channel;
    be u16 scan;
    be u16 set_speed;
    be u16 speed;
    be s16 temperature; // *10
    be float w2t;
    be s32 seconds;
    be u16 radius_count;
    be u16 radius_start; // *1000
    be u16 radius_step; // *10000
    be u16 lambda_count;
    be u16 lambda[lambda_count]; 
    be s32 reading[lambda_count*radius_count];
    
};

MWRS test @ 0x00;