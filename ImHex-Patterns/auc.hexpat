#pragma description AUC .auc file
#pragma author Doluk
#pragma MIME application/auc

struct AUCScan {
    char data_type[4];
    le float temp;
    le float rmp;
    le s32 seconds;
    le float omega2t;
    le s16 raw_lambda;
    float lambda = float(raw_lambda) / 10.0;
    le float delta_r;
    le s32 reading_count;
    le u16 readings[reading_count];
    char interpolated[(reading_count+7)/8];
};


struct AUC {
    be char magic[4];
    char version[2];
    char data_type[2];
    le u8 cell;
    char channel;
    char guid[16];
    char description[240];
    le float min_radius;
    le float min_radius2;
    le float delta_radius;
    le float min_data1;
    le float max_data1;
    le float min_data2;
    le float max_data2;
    le s16 scan_count;
    
    
    AUCScan scans[scan_count];
    
};

AUC test @ 0x00;