import { Search } from "lucide-react";
import { Input } from "@/shared/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";

export type SortKey = "priority" | "created_at" | "updated_at";

interface KanbanFiltersProps {
  search: string;
  onSearchChange: (v: string) => void;
  priority: string;
  onPriorityChange: (v: string) => void;
  sort: SortKey;
  onSortChange: (v: SortKey) => void;
}

export function KanbanFilters({ search, onSearchChange, priority, onPriorityChange, sort, onSortChange }: KanbanFiltersProps) {
  return (
    <div className="flex gap-2 flex-wrap mb-4">
      <div className="relative flex-1 min-w-[180px]">
        <Search className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground" />
        <Input
          placeholder="Search issues..."
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-8 h-8 text-sm"
        />
      </div>
      <Select value={priority} onValueChange={onPriorityChange}>
        <SelectTrigger className="w-[120px] h-8 text-sm">
          <SelectValue placeholder="Priority" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All</SelectItem>
          <SelectItem value="1">P1</SelectItem>
          <SelectItem value="2">P2</SelectItem>
          <SelectItem value="3">P3</SelectItem>
          <SelectItem value="4">P4</SelectItem>
          <SelectItem value="5">P5</SelectItem>
        </SelectContent>
      </Select>
      <Select value={sort} onValueChange={(v) => onSortChange(v as SortKey)}>
        <SelectTrigger className="w-[140px] h-8 text-sm">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="priority">By priority</SelectItem>
          <SelectItem value="created_at">By created date</SelectItem>
          <SelectItem value="updated_at">By last updated</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}
