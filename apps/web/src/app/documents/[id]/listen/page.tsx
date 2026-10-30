import { Suspense } from "react";
import { Reader, ReaderSkeleton } from "@/components/reader/reader";

// Not async (Cache Components): the shell is static, the document streams in.
// Extra bottom padding keeps the last lines clear of the fixed player bar.
export default function ListenPage({ params }: { params: Promise<{ id: string }> }) {
  return (
    <main className="w-full px-4 pt-32 pb-56 md:px-8 md:pt-40">
      <Suspense fallback={<ReaderSkeleton />}>
        <Reader params={params} />
      </Suspense>
    </main>
  );
}
