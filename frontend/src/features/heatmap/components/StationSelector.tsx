"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Station } from "@/types/api";

interface StationSelectorProps {
  stations: Station[];
  selectedId: number | null;
  onSelect: (stationId: number) => void;
}

export function StationSelector({
  stations,
  selectedId,
  onSelect,
}: StationSelectorProps) {
  return (
    <Select
      value={selectedId?.toString() ?? ""}
      onValueChange={(value) => onSelect(Number(value))}
    >
      <SelectTrigger className="w-[200px]">
        <SelectValue placeholder="地点を選択" />
      </SelectTrigger>
      <SelectContent>
        {stations.map((station) => (
          <SelectItem key={station.id} value={station.id.toString()}>
            {station.station_name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
