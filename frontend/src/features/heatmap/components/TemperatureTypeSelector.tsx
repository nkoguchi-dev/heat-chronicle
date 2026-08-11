import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

import { TEMP_TYPE_LABELS, type TempType } from '../types/api';

interface TemperatureTypeSelectorProps {
  value: TempType;
  onChange: (value: string) => void;
}

export function TemperatureTypeSelector({ value, onChange }: TemperatureTypeSelectorProps): React.JSX.Element {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="w-full md:w-[140px]" aria-label="気温種別">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {(Object.entries(TEMP_TYPE_LABELS) as [TempType, string][]).map(([type, label]) => (
          <SelectItem key={type} value={type}>
            {label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
