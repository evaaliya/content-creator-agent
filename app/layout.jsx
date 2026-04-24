import './globals.css';

export const metadata = {
  title: 'Matricula Agent Dashboard',
  description: 'Cyberpunk Asset Gallery and Autonomous Farcaster Agent',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  );
}
