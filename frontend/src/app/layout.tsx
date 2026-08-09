import '@/app/globals.css';

export const metadata = {
  title: 'DeepBlender',
  description: 'Plateforme de production audiovisuelle assistée par agents IA (NOOA + Blender)',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body className="min-h-screen bg-gray-950 text-gray-100 font-sans antialiased">
        {children}
      </body>
    </html>
  );
}