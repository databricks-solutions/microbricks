import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";

/**
 * Reusable pagination + page-size control for list pages.
 *
 * Drives off `(total, limit, offset)` rather than `(page, pageSize)` because
 * the BFF speaks the offset/limit dialect — converting once at the edge is
 * simpler than threading two dialects through the codebase.
 *
 * Behaviour:
 *  - Disables prev/first when on page 1, next/last when on the last page.
 *  - Renders "X – Y of Z" so the user always knows where they are even when
 *    a search/filter narrows the visible window.
 *  - Page-size change resets to the first page (offset = 0).
 *  - Hides itself when there's only one page AND the page-size selector
 *    isn't needed — keeps unused chrome off short result lists.
 */
export interface PaginationProps {
  total: number;
  limit: number;
  offset: number;
  onOffsetChange: (offset: number) => void;
  onLimitChange?: (limit: number) => void;
  pageSizeOptions?: number[];
  className?: string;
}

const DEFAULT_PAGE_SIZES = [25, 50, 100, 200];

export function Pagination({
  total,
  limit,
  offset,
  onOffsetChange,
  onLimitChange,
  pageSizeOptions = DEFAULT_PAGE_SIZES,
  className,
}: PaginationProps) {
  const page = Math.floor(offset / limit) + 1;
  const pageCount = Math.max(1, Math.ceil(total / limit));
  const firstRow = total === 0 ? 0 : offset + 1;
  const lastRow = Math.min(total, offset + limit);

  if (pageCount <= 1 && !onLimitChange) return null;

  const go = (p: number) => {
    const clamped = Math.max(1, Math.min(pageCount, p));
    onOffsetChange((clamped - 1) * limit);
  };

  return (
    <div
      className={`flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between ${className ?? ""}`}
    >
      <p className="text-xs text-muted-foreground">
        {total === 0
          ? "No results"
          : `Showing ${firstRow.toLocaleString()}–${lastRow.toLocaleString()} of ${total.toLocaleString()}`}
      </p>
      <div className="flex items-center gap-2">
        {onLimitChange && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="hidden sm:inline">Per page</span>
            <Select
              value={limit}
              onChange={(e) => {
                onLimitChange(Number(e.target.value));
                onOffsetChange(0);
              }}
              className="h-8 w-[80px] text-xs"
            >
              {pageSizeOptions.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </Select>
          </div>
        )}
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => go(1)}
            disabled={page <= 1}
            aria-label="First page"
          >
            <ChevronsLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => go(page - 1)}
            disabled={page <= 1}
            aria-label="Previous page"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="px-2 text-xs tabular-nums text-muted-foreground min-w-[60px] text-center">
            {page} / {pageCount}
          </span>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => go(page + 1)}
            disabled={page >= pageCount}
            aria-label="Next page"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => go(pageCount)}
            disabled={page >= pageCount}
            aria-label="Last page"
          >
            <ChevronsRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
