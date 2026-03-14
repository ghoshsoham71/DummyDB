"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table";
import { Search, Download, Filter } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const mockData = [
    { id: 1, name: "John Doe", email: "john@example.com", age: 28, city: "New York" },
    { id: 2, name: "Jane Smith", email: "jane@example.com", age: 34, city: "London" },
    { id: 3, name: "Bob Johnson", email: "bob@example.com", age: 45, city: "Paris" },
    { id: 4, name: "Alice Brown", email: "alice@example.com", age: 22, city: "Berlin" },
];

export default function DataExplorerPage() {
  return (
    <div className="container mx-auto py-8 space-y-6">
      <div className="flex justify-between items-center bg-card p-6 rounded-xl border border-primary/20 shadow-lg">
        <div className="flex-1 max-w-md">
            <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input placeholder="Search synthetic records..." className="pl-10 bg-muted/50 border-none h-11" />
            </div>
        </div>
        <div className="flex gap-3">
            <Button variant="outline" className="gap-2">
                <Filter className="w-4 h-4" /> Filter
            </Button>
            <Button className="gap-2 shadow-lg shadow-primary/20">
                <Download className="w-4 h-4" /> Export CSV
            </Button>
        </div>
      </div>

      <Card className="border-primary/20 shadow-xl overflow-hidden">
        <CardContent className="p-0">
          <Table>
            <TableHeader className="bg-muted/50">
              <TableRow>
                <TableHead className="font-bold">ID</TableHead>
                <TableHead className="font-bold">Name</TableHead>
                <TableHead className="font-bold">Email</TableHead>
                <TableHead className="font-bold">Age</TableHead>
                <TableHead className="font-bold">City</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockData.map((row) => (
                <TableRow key={row.id} className="hover:bg-primary/5 transition-colors">
                  <TableCell className="font-mono text-xs">{row.id}</TableCell>
                  <TableCell className="font-medium">{row.name}</TableCell>
                  <TableCell>{row.email}</TableCell>
                  <TableCell>{row.age}</TableCell>
                  <TableCell>{row.city}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
      
      <div className="flex justify-center">
          <div className="flex items-center gap-2 text-xs text-muted-foreground font-bold uppercase tracking-widest">
              <span>Page 1 of 128</span>
              <div className="w-32 h-1.5 bg-muted rounded-full overflow-hidden">
                  <div className="bg-primary h-full w-1/4" />
              </div>
          </div>
      </div>
    </div>
  );
}
