import type { Metadata } from "next";
import { Head } from "nextra/components";
import "./globals.css";
import { Geist, Geist_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/theme-provider";
import { Layout, Navbar } from "nextra-theme-docs";
import { getPageMap } from "nextra/page-map";
import { Footer } from "@/components/Footer";
import { ModeToggle } from "@/components/ModeToggle";
import "nextra-theme-docs/style.css";
export const metadata: Metadata = {
  title: "BurstDB",
  description: "Testing",
};

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const navbar = (
  <Navbar
    logo={<b>BurstDB</b>}
    projectLink="https://github.com/ghoshsoham71/BurstDB"
  >
    <ModeToggle />
  </Navbar>
);
const footer = <Footer></Footer>;
const feedback = {
  // content: null,
  labels: "feedback",
  // ... Your additional feedback options
  // For more information on feedback API, see: https://nextra.vercel.app/docs/feedback
};
const sidebar = {
  toggleButton: false,
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" dir="ltr" suppressHydrationWarning>
      <Head
      // ... Your additional head options
      >
        {/* Your additional tags should be passed as `children` of `<Head>` element */}
      </Head>
      <body className={`${geistSans.variable} ${geistMono.variable} font-geist-sans antialiased`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <Layout
            navbar={navbar}
            pageMap={await getPageMap()}
            docsRepositoryBase="https://github.com/ghoshsoham71/BurstDB/tree/main/ui"
            footer={footer}
            // editLink={null}
            feedback={feedback}
            darkMode={false}
            sidebar={sidebar}

            // ... Your additional layout options
          >
            {children}
          </Layout>
        </ThemeProvider>
      </body>
    </html>
  );
}
