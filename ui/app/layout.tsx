import type { Metadata } from "next";
import { Head } from "nextra/components";
import "./globals.css";
import { Raleway } from "next/font/google";
import { ThemeProvider } from "@/components/theme-provider";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Layout, Navbar } from "nextra-theme-docs";
import { getPageMap } from "nextra/page-map";
import { Footer } from "@/components/layout/Footer";
import { ModeToggle } from "@/components/shared/ModeToggle";
import "nextra-theme-docs/style.css";
export const metadata: Metadata = {
  title: "BurstDB",
  description: "Testing",
};

const ralewayFont = Raleway({
  variable: "--font-raleway",
  subsets: ["latin"],
  weight: ["200", "300", "400", "500", "600", "700", "800", "900"],
});

import { CustomLogo } from "@/components/layout/CustomLogo";

const navbar = (
  <Navbar
    logo={<CustomLogo />}
    projectLink="https://github.com/ghoshsoham71/BurstDB"
  >
    <div className="flex items-center gap-2">
      <ModeToggle />
      <NavbarAuth />
    </div>
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

import { AuthProvider } from "@/lib/auth-context";
import { NavbarAuth } from "@/components/layout/NavbarAuth";
import { ConditionalSearch } from "@/components/shared/ConditionalSearch";
import { HideNavLinks } from "@/components/layout/HideNavLinks";

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
      <body className={`${ralewayFont.variable} font-sans antialiased`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <ConditionalSearch />
          <HideNavLinks />
          <TooltipProvider>
            <AuthProvider>
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
            </AuthProvider>
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
