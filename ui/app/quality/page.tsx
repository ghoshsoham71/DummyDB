"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from "recharts";
import { ShieldCheck, Zap, Activity } from "lucide-react";

const mockFidelityData = [
  { name: "Age", real: 0.85, synthetic: 0.82 },
  { name: "Income", real: 0.75, synthetic: 0.70 },
  { name: "Location", real: 0.95, synthetic: 0.92 },
  { name: "Balance", real: 0.65, synthetic: 0.68 },
];

export default function QualityReportPage() {
  return (
    <div className="container mx-auto py-8 space-y-8">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-black tracking-tight flex items-center gap-3">
            <ShieldCheck className="w-8 h-8 text-green-500" />
            Fidelity & Privacy Audit
          </h1>
          <p className="text-muted-foreground mt-1">Automated validation of synthetic data integrity.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="border-green-500/20 bg-green-500/5">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
                <div className="p-3 bg-green-500/20 rounded-lg">
                    <Zap className="w-6 h-6 text-green-600" />
                </div>
                <div>
                    <p className="text-xs font-bold text-muted-foreground uppercase">TVD Score</p>
                    <p className="text-2xl font-black">0.89</p>
                </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-blue-500/20 bg-blue-500/5">
           <CardContent className="pt-6">
            <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-500/20 rounded-lg">
                    <Activity className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                    <p className="text-xs font-bold text-muted-foreground uppercase">KS-Test Pass</p>
                    <p className="text-2xl font-black">94%</p>
                </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-purple-500/20 bg-purple-500/5">
            <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-purple-500/20 rounded-lg">
                        <ShieldCheck className="w-6 h-6 text-purple-600" />
                    </div>
                <div>
                    <p className="text-xs font-bold text-muted-foreground uppercase">Privacy Risk</p>
                    <p className="text-2xl font-black text-green-600">LOW</p>
                </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg font-bold">Column Distribution Fidelity</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={mockFidelityData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} strokeOpacity={0.1} />
                <XAxis dataKey="name" axisLine={false} tickLine={false} fontSize={12} />
                <YAxis axisLine={false} tickLine={false} fontSize={12} />
                <Tooltip 
                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }}
                />
                <Bar dataKey="real" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} fillOpacity={0.3} />
                <Bar dataKey="synthetic" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg font-bold">Privacy Disclosure Risk (DCR)</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px]">
             <ResponsiveContainer width="100%" height="100%">
              <LineChart data={mockFidelityData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} strokeOpacity={0.1} />
                <XAxis dataKey="name" axisLine={false} tickLine={false} fontSize={12} />
                <YAxis axisLine={false} tickLine={false} fontSize={12} />
                <Tooltip />
                <Line type="monotone" dataKey="real" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
