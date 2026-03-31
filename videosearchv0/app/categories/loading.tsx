import { Card, CardContent } from "@/components/ui/card"

export default function Loading() {
  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <div className="text-center space-y-4 mb-12">
          <div className="h-10 bg-muted rounded-lg w-64 mx-auto animate-pulse" />
          <div className="h-6 bg-muted rounded-lg w-96 mx-auto animate-pulse" />
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {Array.from({ length: 12 }, (_, i) => (
            <Card key={i} className="overflow-hidden">
              <CardContent className="p-6 text-center space-y-4">
                <div className="w-16 h-16 bg-muted rounded-2xl mx-auto animate-pulse" />
                <div className="space-y-2">
                  <div className="h-5 bg-muted rounded w-24 mx-auto animate-pulse" />
                  <div className="h-4 bg-muted rounded w-16 mx-auto animate-pulse" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}
