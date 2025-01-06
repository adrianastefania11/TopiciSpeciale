using System;
using System.IO;
using MailKit.Net.Imap;
using MailKit;
using MimeKit;
using System.Net.Mail;
using MailKit.Search;

class Program
{
    static void Main(string[] args)
    {
        string email = "email";
        string password = "password";
        string imapServer = "imap.gmail.com"; // Serverul IMAP (ex. Gmail)
        int port = 993; // Portul IMAP pentru conexiune securizată
        string downloadFolder = @"path";
        // Crearea directorului pentru atașamente dacă nu există
        if (!Directory.Exists(downloadFolder))
        {
            Directory.CreateDirectory(downloadFolder);
        }

        using (var client = new ImapClient())
        {
            try
            {
                // Conectare la server
                client.Connect(imapServer, port, true);

                // Autentificare
                client.Authenticate(email, password);

                // Accesarea inbox-ului
                var inbox = client.Inbox;
                inbox.Open(FolderAccess.ReadOnly);

                // Filtrarea mesajelor din ziua curentă
                var today = DateTime.UtcNow.Date; // Folosește UTC pentru consistență
                var query = SearchQuery.DeliveredAfter(today.AddDays(-1))
                                        .And(SearchQuery.DeliveredBefore(today.AddDays(1)));

                var uids = inbox.Search(query);

                Console.WriteLine($"Număr de mesaje găsite astăzi: {uids.Count}");

                foreach (var uid in uids)
                {
                    var message = inbox.GetMessage(uid);
                    Console.WriteLine($"Procesăm mesajul: {message.Subject}");

                    // Verificăm atașamentele
                    if (message.Attachments != null)
                    {
                        foreach (var attachment in message.Attachments)
                        {
                            if (attachment is MimePart mimePart)
                            {
                                var fileName = mimePart.FileName;

                                // Salvăm atașamentul pe disc
                                var filePath = Path.Combine(downloadFolder, fileName);
                                using (var stream = File.Create(filePath))
                                {
                                    mimePart.Content.DecodeTo(stream);
                                }

                                Console.WriteLine($"Atașamentul '{fileName}' a fost salvat în {downloadFolder}");
                            }
                        }
                    }
                }

                // Deconectare de la server
                client.Disconnect(true);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"A apărut o eroare: {ex.Message}");
            }
        }
    }
}
