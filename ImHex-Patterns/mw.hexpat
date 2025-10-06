#pragma description AUC .mw file
#pragma author Doluk
#pragma MIME application/mw

struct Reading {
    be u32 radius;
    be u32 lambda;
};

struct MWfile {
    be u32 magic_number;
    be u48 date_time;
    be u16 version;
    be u8  cell;
    be char channel;
    be u16 scan;
    be char sample[64];
    be u16 speed;
    be u16 temp;
    be u32 w2t;
    be u32 seconds;
    be u16 radius_count;
    be u16 radius_start;
    be u16 radius_end;
    be u16 lambda_count;
    be u16 lambda[lambda_count];
    be u32 readings[lambda_count*radius_count];
 };
 
MWfile test @ 0x00;