#pragma description AUC .tmst file
#pragma author Doluk
#pragma MIME application/tmst

#include "std/mem"
struct TMSTRecord {
    be u32 time;
    be float raw_speed;
    be u32 set_speed;
    be float omega2t;
    be float temperature;
    be u16 step;
    be u16 scan;
};

struct TMSTRecords { 
    TMSTRecord records[];
};

struct TMST {
    padding[4];
    be char major_version;
    be char minor_version;
    TMSTRecord records[while(!std::mem::eof())];
};
 
TMST test @ 0x00;