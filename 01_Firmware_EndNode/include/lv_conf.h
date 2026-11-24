#if 1
#ifndef LV_CONF_H
#define LV_CONF_H

#include <stdint.h>

#define LV_COLOR_DEPTH 16
#define LV_COLOR_16_SWAP 0
#define LV_MEM_SIZE (32U * 1024U)
#define LV_MEM_ATTR
#define LV_MEM_ADR 0
#define LV_MEMCPY_MEMSET_STD 0
#define LV_DISP_DEF_REFR_PERIOD 30
#define LV_INDEV_DEF_READ_PERIOD 30
#define LV_DPI_DEF 130
#define LV_TICK_CUSTOM 0
#define LV_USE_LOG 0
#define LV_USE_ASSERT_NULL 1
#define LV_USE_ASSERT_MALLOC 1

#define LV_FONT_MONTSERRAT_12 1
#define LV_FONT_MONTSERRAT_14 1
#define LV_FONT_MONTSERRAT_32 1
#define LV_FONT_DEFAULT &lv_font_montserrat_14

#define LV_USE_LABEL 1
#define LV_USE_OBJ 1
#define LV_USE_THEME_DEFAULT 1
#define LV_THEME_DEFAULT_DARK 1
#define LV_USE_THEME_BASIC 1
#define LV_USE_THEME_MONO 1
#define LV_USE_FLEX 1
#define LV_USE_GRID 1

#endif
#endif
