import { z } from 'zod';

import type {
  MonthTemperatureResponse,
  Prefecture,
  Station,
  TemperatureRecord,
  TemperatureResponse,
} from '@/features/heatmap/types/api';

const temperatureRecordSchema: z.ZodType<TemperatureRecord> = z.object({
  date: z.iso.date(),
  max_temp: z.number().nullable(),
  min_temp: z.number().nullable(),
  avg_temp: z.number().nullable(),
});

const prefectureSchema: z.ZodType<Prefecture> = z.object({
  prec_no: z.number(),
  name: z.string(),
});

const stationSchema: z.ZodType<Station> = z.object({
  id: z.number(),
  station_name: z.string(),
  prec_no: z.number(),
  block_no: z.string(),
  station_type: z.enum(['s', 'a']),
  latitude: z.number().nullable(),
  longitude: z.number().nullable(),
  earliest_year: z.number().nullable(),
});

export const prefecturesResponseSchema: z.ZodType<Prefecture[]> = z.array(prefectureSchema);
export const stationsResponseSchema: z.ZodType<Station[]> = z.array(stationSchema);

export const temperatureResponseSchema: z.ZodType<TemperatureResponse> = z.object({
  metadata: z.object({
    station_id: z.number(),
    station_name: z.string(),
    start_year: z.number(),
    end_year: z.number(),
    total_records: z.number(),
    fetched_months: z.array(z.string()),
    fetching_required: z.boolean(),
    has_older_data: z.boolean(),
    next_end_year: z.number().nullable(),
  }),
  data: z.array(temperatureRecordSchema),
});

export const monthTemperatureResponseSchema: z.ZodType<MonthTemperatureResponse> = z.object({
  year: z.number(),
  month: z.number(),
  records: z.array(temperatureRecordSchema),
});
