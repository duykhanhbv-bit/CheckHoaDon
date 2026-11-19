using System;
using System.IO;
using System.Diagnostics;

namespace CheckHoaDonLauncher
{
    class Program
    {
        static Process pythonProc = null;

        static void Main(string[] args)
        {
            string baseDir = AppDomain.CurrentDomain.BaseDirectory;
            Directory.SetCurrentDirectory(baseDir);

            string verFile = Path.Combine(baseDir, "VERSION.txt");
            string versionStr = File.Exists(verFile) ? ("v" + File.ReadAllText(verFile).Trim()) : "v1.1";
            Console.Title = "TRA CUU HOA DON DIEN TU & NNT TU DONG (" + versionStr + ") - RPA PLAYWRIGHT";

            Console.WriteLine("================================================================");
            Console.WriteLine("  HE THONG TRA CUU HOA DON DIEN TU & NNT TU DONG - " + versionStr + " ");
            Console.WriteLine("================================================================");
            Console.WriteLine();

            // Setup Environment
            Environment.SetEnvironmentVariable("PYTHONUTF8", "1");
            Environment.SetEnvironmentVariable("PYTHONIOENCODING", "utf-8");

            string pwBrowsers = Path.Combine(baseDir, "pw-browsers");
            if (Directory.Exists(pwBrowsers))
            {
                Environment.SetEnvironmentVariable("PLAYWRIGHT_BROWSERS_PATH", pwBrowsers);
            }

            // Locate Python
            string pyExe = Path.Combine(baseDir, "python_env", "python.exe");
            if (!File.Exists(pyExe))
            {
                pyExe = "python.exe";
            }

            // Check / Self-healing requirements
            try
            {
                ProcessStartInfo psiCheck = new ProcessStartInfo(pyExe, "-c \"import fastapi, playwright, ddddocr, pymupdf, pdfplumber, PIL, anyio, sniffio, pydantic, uvicorn\"");
                psiCheck.UseShellExecute = false;
                psiCheck.CreateNoWindow = true;
                psiCheck.WorkingDirectory = baseDir;
                Process pCheck = Process.Start(psiCheck);
                pCheck.WaitForExit();
                if (pCheck.ExitCode != 0)
                {
                    Console.ForegroundColor = ConsoleColor.Yellow;
                    Console.WriteLine("[CANH BAO] Dang tu dong cap nhat cac thu vien con thieu...");
                    Console.ForegroundColor = ConsoleColor.Green;
                    
                    string reqFile = Path.Combine(baseDir, "requirements.txt");
                    if (File.Exists(reqFile))
                    {
                        ProcessStartInfo psiPip = new ProcessStartInfo(pyExe, "-m pip install -r \"" + reqFile + "\"");
                        psiPip.UseShellExecute = false;
                        psiPip.WorkingDirectory = baseDir;
                        Process pPip = Process.Start(psiPip);
                        pPip.WaitForExit();
                    }
                }
            }
            catch { }

            // Handle Ctrl+C and exit
            Console.CancelKeyPress += delegate(object sender, ConsoleCancelEventArgs e)
            {
                KillPython();
            };
            AppDomain.CurrentDomain.ProcessExit += delegate(object sender, EventArgs e)
            {
                KillPython();
            };

            Console.ResetColor();

            // Launch smart start_app.py
            try
            {
                string startScript = Path.Combine(baseDir, "start_app.py");
                string argsStr = "\"" + startScript + "\"";
                if (args.Length > 0)
                {
                    argsStr += " " + string.Join(" ", args);
                }

                ProcessStartInfo psi = new ProcessStartInfo(pyExe, argsStr);
                psi.UseShellExecute = false;
                psi.WorkingDirectory = baseDir;
                pythonProc = Process.Start(psi);
                pythonProc.WaitForExit();
            }
            catch (Exception ex)
            {
                Console.ForegroundColor = ConsoleColor.Red;
                Console.WriteLine("[LOI] Khong the khoi dong: " + ex.Message);
                Console.ResetColor();
                Console.WriteLine("Nhan phim bat ky de thoat...");
                Console.ReadKey();
            }
        }

        static void KillPython()
        {
            try
            {
                if (pythonProc != null && !pythonProc.HasExited)
                {
                    pythonProc.Kill();
                }
            }
            catch { }
        }
    }
}
