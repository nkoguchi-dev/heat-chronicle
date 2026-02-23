import { useMemo } from "react";

import type { TempType } from "@/types/api";

interface UrlParams {
  station: number | null;
  pref: number | null;
  type: TempType;
}

const VALID_TEMP_TYPES: TempType[] = ["max", "min", "avg"];
const DEFAULT_PREF = 44;
const DEFAULT_STATION = 4;

function parseParams(): UrlParams {
  if (typeof window === "undefined") {
    return { station: DEFAULT_STATION, pref: DEFAULT_PREF, type: "max" };
  }

  const params = new URLSearchParams(window.location.search);

  const stationRaw = params.get("station");
  const prefRaw = params.get("pref");
  const typeRaw = params.get("type");

  const station =
    stationRaw !== null && /^\d+$/.test(stationRaw)
      ? Number(stationRaw)
      : null;
  const pref =
    prefRaw !== null && /^\d+$/.test(prefRaw) ? Number(prefRaw) : null;
  const type =
    typeRaw !== null && VALID_TEMP_TYPES.includes(typeRaw as TempType)
      ? (typeRaw as TempType)
      : "max";

  if (station === null && pref === null) {
    const url = new URL(window.location.href);
    url.searchParams.set("pref", String(DEFAULT_PREF));
    url.searchParams.set("station", String(DEFAULT_STATION));
    window.history.replaceState(null, "", url.toString());
    return { station: DEFAULT_STATION, pref: DEFAULT_PREF, type };
  }

  return { station, pref, type };
}

function updateUrl(params: Partial<UrlParams>) {
  const url = new URL(window.location.href);

  if (params.pref !== undefined) {
    if (params.pref !== null) {
      url.searchParams.set("pref", String(params.pref));
    } else {
      url.searchParams.delete("pref");
    }
  }

  if (params.station !== undefined) {
    if (params.station !== null) {
      url.searchParams.set("station", String(params.station));
    } else {
      url.searchParams.delete("station");
    }
  }

  if (params.type !== undefined) {
    if (params.type === "max") {
      url.searchParams.delete("type");
    } else {
      url.searchParams.set("type", params.type);
    }
  }

  window.history.replaceState(null, "", url.toString());
}

export function useUrlParams() {
   
  const initialParams = useMemo(() => parseParams(), []);

  return { initialParams, updateUrl };
}
