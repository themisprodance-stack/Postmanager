"""Greek translations of every user-facing text. Keys are the English texts exactly as they appear in the code
and templates. After editing, run:  .venv/bin/python manage.py build_translations"""

EL = {
    # --- Navigation & general ---
    "Home": "Αρχική",
    "Posts": "Αναρτήσεις",
    "Library": "Βιβλιοθήκη",
    "Recurring": "Επαναλαμβανόμενες",
    "Queue": "Ουρά",
    "Stats": "Στατιστικά",
    "Links page": "Σελίδα συνδέσμων",
    "Team": "Ομάδα",
    "Language": "Γλώσσα",
    "Account settings": "Ρυθμίσεις λογαριασμού",
    "Log out": "Αποσύνδεση",
    "Sign out": "Αποσύνδεση",
    "Save": "Αποθήκευση",
    "Cancel": "Ακύρωση",
    "Edit": "Επεξεργασία",
    "Delete": "Διαγραφή",
    "Remove": "Αφαίρεση",
    "Copy": "Αντιγραφή",
    "Copied ✓": "Αντιγράφηκε ✓",
    "Copy this:": "Αντιγράψτε αυτό:",
    "All": "Όλες",
    "Name": "Όνομα",
    "Type": "Τύπος",
    "When": "Πότε",
    "Days": "Ημέρες",
    "Day": "Ημέρα",
    "Hour": "Ώρα",
    "Time(s)": "Ώρα/ες",
    "Active": "Ενεργή",
    "Paused": "Σε παύση",
    "Next": "Επόμενη",
    "Next:": "Επόμενη:",
    "Next post": "Επόμενη ανάρτηση",
    "Next post:": "Επόμενη ανάρτηση:",
    "then": "μετά",
    "never": "ποτέ",
    "random": "τυχαία",
    "you": "εσείς",
    "(optional)": "(προαιρετικό)",
    "Link": "Σύνδεσμος",
    "Caption": "Λεζάντα",
    "Captions": "Λεζάντες",
    "Video": "Βίντεο",
    "Videos": "Βίντεο",
    "Photo": "Φωτογραφία",
    "Photos": "Φωτογραφίες",
    "Photos & videos": "Φωτογραφίες & βίντεο",
    "Photos or videos": "Φωτογραφίες ή βίντεο",
    "Mon": "Δευ",
    "Tue": "Τρι",
    "Wed": "Τετ",
    "Thu": "Πεμ",
    "Fri": "Παρ",
    "Sat": "Σαβ",
    "Sun": "Κυρ",
    "Something went wrong.": "Κάτι πήγε στραβά.",
    "Bad request.": "Μη έγκυρο αίτημα.",
    "Not saved yet. Please fix:": "Δεν αποθηκεύτηκε ακόμη. Διορθώστε:",
    "Saved.": "Αποθηκεύτηκε.",

    # --- Banners ---
    "Instagram isn't connected yet, so nothing can be published.":
        "Το Instagram δεν έχει συνδεθεί ακόμη, οπότε δεν μπορεί να δημοσιευτεί τίποτα.",
    "Connect it →": "Σύνδεση →",
    "Ask an owner to connect it.": "Ζητήστε από έναν ιδιοκτήτη να το συνδέσει.",
    "The Instagram connection expires soon and couldn't be renewed automatically.":
        "Η σύνδεση με το Instagram λήγει σύντομα και δεν ανανεώθηκε αυτόματα.",
    "Reconnect →": "Επανασύνδεση →",
    "Automatic publishing isn't running": "Η αυτόματη δημοσίευση δεν λειτουργεί",
    "so scheduled, recurring and queued posts won't go out on time.":
        "οπότε οι προγραμματισμένες, επαναλαμβανόμενες και αναρτήσεις ουράς δεν θα βγουν στην ώρα τους.",
    "Fix it (2 minutes) →": "Διόρθωση (2 λεπτά) →",
    "Photo & video storage isn't connected yet, so uploading is switched off. An owner needs to connect Blob storage in the Vercel project (Storage tab).":
        "Ο χώρος αποθήκευσης φωτογραφιών & βίντεο δεν έχει συνδεθεί ακόμη, οπότε το ανέβασμα είναι απενεργοποιημένο. "
        "Ένας ιδιοκτήτης πρέπει να συνδέσει αποθήκευση Blob στο έργο Vercel (καρτέλα Storage).",

    # --- Dashboard ---
    "Hi %(name)s 👋": "Γεια σου %(name)s 👋",
    "Hi there 👋": "Γεια σου 👋",
    "Posting as <b>%(account)s</b>": "Δημοσίευση ως <b>%(account)s</b>",
    "Not connected to Instagram": "Χωρίς σύνδεση με το Instagram",
    "+ New post": "+ Νέα ανάρτηση",
    "Scheduled": "Προγραμματισμένες",
    "Published in the last 7 days": "Δημοσιεύτηκαν τις τελευταίες 7 ημέρες",
    "Drafts": "Πρόχειρα",
    "Items ready for the queue": "Στοιχεία έτοιμα για την ουρά",
    "Needs attention": "Χρειάζεται προσοχή",
    "Coming up": "Έρχονται",
    "Nothing scheduled.": "Δεν υπάρχει τίποτα προγραμματισμένο.",
    "Plan a post": "Προγραμματίστε μια ανάρτηση",
    "Automations": "Αυτοματισμοί",
    "Queue on": "Ουρά ενεργή",
    "Queue off": "Ουρά ανενεργή",
    "Content queue": "Ουρά περιεχομένου",
    "Turn on to post from your library automatically.": "Ενεργοποιήστε την για αυτόματες αναρτήσεις από τη βιβλιοθήκη σας.",
    "+ Add a recurring post": "+ Προσθήκη επαναλαμβανόμενης ανάρτησης",
    "Recently published": "Πρόσφατες δημοσιεύσεις",
    "Nothing published yet.": "Δεν έχει δημοσιευτεί τίποτα ακόμη.",

    # --- Post list & rows ---
    "No posts here yet.": "Δεν υπάρχουν αναρτήσεις εδώ ακόμη.",
    "(no caption)": "(χωρίς λεζάντα)",
    "Retry now": "Νέα προσπάθεια",
    "View on Instagram": "Προβολή στο Instagram",
    "Duplicate": "Αντίγραφο",
    "Delete this post from Postmanager?": "Διαγραφή αυτής της ανάρτησης από το Postmanager;",
    "Delete this post from Postmanager? (It stays on Instagram.)":
        "Διαγραφή αυτής της ανάρτησης από το Postmanager; (Παραμένει στο Instagram.)",
    "Photo post": "Ανάρτηση φωτογραφίας",
    "Carousel": "Καρουζέλ",
    "Reel": "Reel",
    "Story": "Story",
    "Draft": "Πρόχειρο",
    "Publishing": "Δημοσιεύεται",
    "Published": "Δημοσιεύτηκε",
    "Failed": "Απέτυχε",
    "Manual": "Χειροκίνητη",

    # --- Post form ---
    "New post": "Νέα ανάρτηση",
    "Edit post": "Επεξεργασία ανάρτησης",
    "Failed:": "Απέτυχε:",
    "Tap to select from your library. For carousels, the order you tap is the order shown.":
        "Πατήστε για επιλογή από τη βιβλιοθήκη σας. Στο καρουζέλ, η σειρά που πατάτε είναι η σειρά εμφάνισης.",
    "…or upload new": "…ή ανεβάστε νέα",
    "Upload photos or videos": "Ανέβασμα φωτογραφιών ή βίντεο",
    "Write captions with AI": "Γράψτε λεζάντες με AI",
    "e.g. Line dance social night last Friday, 40 dancers, new beginners class starts Monday":
        "π.χ. Βραδιά line dance την περασμένη Παρασκευή, 40 χορευτές, νέο τμήμα αρχαρίων ξεκινά τη Δευτέρα",
    "Suggest captions": "Προτάσεις λεζάντας",
    "Uses your description and the selected photos.": "Χρησιμοποιεί την περιγραφή σας και τις επιλεγμένες φωτογραφίες.",
    "Added at the end of the caption. Instagram shows caption links as plain text (not clickable). Don't use a “#section” part: Instagram would turn it into a hashtag, so it's removed.":
        "Προστίθεται στο τέλος της λεζάντας. Το Instagram δείχνει τους συνδέσμους της λεζάντας ως απλό κείμενο "
        "(δεν πατιούνται). Μη χρησιμοποιείτε τμήμα «#ενότητα»: το Instagram θα το έκανε hashtag, οπότε αφαιρείται.",
    # --- Music ---
    'Music': 'Μουσική',
    'Music files': 'Αρχεία μουσικής',
    'Photo or video': 'Φωτογραφία ή βίντεο',
    'Pick a photo or video.': 'Επιλέξτε φωτογραφία ή βίντεο.',
    'Pick a song.': 'Επιλέξτε τραγούδι.',
    'Start the song at': 'Έναρξη τραγουδιού στο',
    'Length (seconds)': 'Διάρκεια (δευτερόλεπτα)',
    "Keep the video's own sound, quieter, under the music": 'Κράτηση του ήχου του βίντεο, χαμηλότερα, κάτω από τη μουσική',
    'Use minutes:seconds, e.g. 0:45': 'Γράψτε λεπτά:δευτερόλεπτα, π.χ. 0:45',
    'The song is only %(length)s long.': 'Το τραγούδι διαρκεί μόνο %(length)s.',
    'Your video with music is ready and saved in the Library.': 'Το βίντεο με μουσική είναι έτοιμο και αποθηκεύτηκε στη Βιβλιοθήκη.',
    '%(name)s: music files can be at most 50 MB.': '%(name)s: τα αρχεία μουσικής μπορούν να είναι έως 50 MB.',
    '%(name)s: only MP3, M4A, AAC and WAV music files are supported.': '%(name)s: υποστηρίζονται μόνο αρχεία μουσικής MP3, M4A, AAC και WAV.',
    "%(name)s: this file couldn't be played as music.": '%(name)s: αυτό το αρχείο δεν μπορεί να αναπαραχθεί ως μουσική.',
    'Making the video took too long. Try a shorter video or length.': 'Η δημιουργία του βίντεο άργησε πολύ. Δοκιμάστε μικρότερο βίντεο ή διάρκεια.',
    'This video is too big to add music here (max 150 MB).': 'Το βίντεο είναι πολύ μεγάλο για να προστεθεί μουσική εδώ (έως 150 MB).',
    "This video couldn't be read.": 'Αυτό το βίντεο δεν μπορεί να διαβαστεί.',
    "The video couldn't be made from these files.": 'Δεν ήταν δυνατή η δημιουργία βίντεο από αυτά τα αρχεία.',
    'Songs and sounds you can add to your photos and videos. Use music you have the rights to: Instagram may mute videos with copyrighted songs.': 'Τραγούδια και ήχοι που μπορείτε να προσθέσετε στις φωτογραφίες και τα βίντεό σας. Χρησιμοποιήστε μουσική για την οποία έχετε δικαιώματα: το Instagram μπορεί να κάνει σίγαση σε βίντεο με τραγούδια που προστατεύονται από πνευματικά δικαιώματα.',
    'Make a video with music': 'Δημιουργία βίντεο με μουσική',
    'Upload music': 'Ανέβασμα μουσικής',
    'MP3, M4A, AAC or WAV files, up to 50 MB each. You can select many at once.': 'Αρχεία MP3, M4A, AAC ή WAV, έως 50 MB το καθένα. Μπορείτε να επιλέξετε πολλά μαζί.',
    'Delete this song?': 'Διαγραφή αυτού του τραγουδιού;',
    'No music yet. Upload some above.': 'Δεν υπάρχει μουσική ακόμα. Ανεβάστε από πάνω.',
    'Pick a photo or video and a song. The new video is saved in your Library, ready for a Story or Reel.': 'Επιλέξτε φωτογραφία ή βίντεο και ένα τραγούδι. Το νέο βίντεο αποθηκεύεται στη Βιβλιοθήκη, έτοιμο για Story ή Reel.',
    'Upload some music first.': 'Ανεβάστε πρώτα λίγη μουσική.',
    'Go to Music →': 'Μετάβαση στη Μουσική →',
    'Start from here': 'Έναρξη από εδώ',
    'Play a song, pause where it should begin, and tap “Start from here”.': 'Παίξτε ένα τραγούδι, σταματήστε εκεί που θέλετε να ξεκινά και πατήστε «Έναρξη από εδώ».',
    'minutes:seconds': 'λεπτά:δευτερόλεπτα',
    'Photos: 3–30 seconds. A video keeps its own length.': 'Φωτογραφίες: 3–30 δευτερόλεπτα. Ένα βίντεο κρατά τη δική του διάρκεια.',
    'Making your video… this can take up to a minute': 'Δημιουργία βίντεο… μπορεί να διαρκέσει έως ένα λεπτό',
    'Make video': 'Δημιουργία βίντεο',
    "Not tagged (private account, wrong username, or they don't allow tags):": "Δεν επισημάνθηκαν (ιδιωτικός λογαριασμός, λάθος όνομα χρήστη ή δεν επιτρέπουν επισημάνσεις):",
    "Tag people": "Επισήμανση ατόμων",
    "Instagram usernames, separated by commas. Only public accounts can be tagged; anyone Instagram can't reach is skipped and the post still goes out. In a carousel, the tags go on the first slide. Stories can't have tags.":
        "Ονόματα χρηστών Instagram, χωρισμένα με κόμμα. Μπορούν να επισημανθούν μόνο δημόσιοι λογαριασμοί· όποιοι δεν είναι προσβάσιμοι παραλείπονται και η ανάρτηση δημοσιεύεται κανονικά. Στο καρουζέλ οι επισημάνσεις μπαίνουν στην πρώτη διαφάνεια. Τα Stories δεν μπορούν να έχουν επισημάνσεις.",
    "Instagram usernames, separated by commas, tagged in every post this creates. Only public accounts can be tagged. Stories are posted without tags.":
        "Ονόματα χρηστών Instagram, χωρισμένα με κόμμα, που επισημαίνονται σε κάθε ανάρτηση που δημιουργείται. Μπορούν να επισημανθούν μόνο δημόσιοι λογαριασμοί. Τα Stories δημοσιεύονται χωρίς επισημάνσεις.",
    "e.g. @maria_dance, @johnsmith": "π.χ. @maria_dance, @johnsmith",
    "“%(name)s” isn't a valid Instagram username.": "Το «%(name)s» δεν είναι έγκυρο όνομα χρήστη Instagram.",
    "Instagram allows at most 20 tagged people.": "Το Instagram επιτρέπει έως 20 επισημασμένα άτομα.",
    "Instagram doesn't allow apps to tag people in Stories. Remove the tags or choose another type.":
        "Το Instagram δεν επιτρέπει σε εφαρμογές να επισημαίνουν άτομα στα Stories. Αφαιρέστε τις επισημάνσεις ή επιλέξτε άλλο τύπο.",
    "Also show this Reel in the main profile grid": "Εμφάνιση του Reel και στο κύριο πλέγμα του προφίλ",
    "Your studio's local time.": "Τοπική ώρα της σχολής σας.",
    "Schedule": "Προγραμματισμός",
    "Publish now": "Δημοσίευση τώρα",
    "Save draft": "Αποθήκευση πρόχειρου",
    "Save as draft": "Αποθήκευση ως πρόχειρο",
    "Publish at": "Δημοσίευση στις",
    "Upload new photos/videos": "Ανέβασμα νέων φωτογραφιών/βίντεο",
    "e.g. lineofdance.gr/classes": "π.χ. lineofdance.gr/classes",
    "Pick a date and time, or save as draft.": "Επιλέξτε ημερομηνία και ώρα ή αποθηκεύστε ως πρόχειρο.",
    "This time is in the past.": "Αυτή η ώρα έχει περάσει.",
    "Added to the end of the caption as text (Instagram never makes caption links clickable).":
        "Προστίθεται στο τέλος της λεζάντας ως κείμενο (το Instagram δεν κάνει ποτέ τους συνδέσμους λεζάντας να πατιούνται).",
    "Reels only: also show in the main grid.": "Μόνο για Reels: εμφάνιση και στο κύριο πλέγμα.",

    # --- Library ---
    "All your photos and videos. Mark items for the queue to have them posted automatically.":
        "Όλες οι φωτογραφίες και τα βίντεό σας. Σημειώστε στοιχεία για την ουρά ώστε να δημοσιεύονται αυτόματα.",
    "JPEG, PNG, HEIC, WebP photos and MP4/MOV videos (up to 300 MB). You can select many at once.":
        "Φωτογραφίες JPEG, PNG, HEIC, WebP και βίντεο MP4/MOV (έως 300 MB). Μπορείτε να επιλέξετε πολλά μαζί.",
    "JPEG, PNG, HEIC, WebP photos and MP4/MOV videos. You can select many at once.":
        "Φωτογραφίες JPEG, PNG, HEIC, WebP και βίντεο MP4/MOV. Μπορείτε να επιλέξετε πολλά μαζί.",
    "Add to the content queue": "Προσθήκη στην ουρά περιεχομένου",
    "Upload": "Ανέβασμα",
    "In queue": "Στην ουρά",
    "✓ In queue": "✓ Στην ουρά",
    "+ Queue": "+ Ουρά",
    "Posted %(n)s×": "Δημοσιεύτηκε %(n)s×",
    "No files yet. Upload some above.": "Δεν υπάρχουν αρχεία ακόμη. Ανεβάστε μερικά παραπάνω.",
    "uploaded %(date)s": "ανέβηκε %(date)s",
    "Queue caption": "Λεζάντα ουράς",
    "Use in a new post": "Χρήση σε νέα ανάρτηση",
    "Delete this file permanently?": "Οριστική διαγραφή αυτού του αρχείου;",
    "Delete file": "Διαγραφή αρχείου",
    "Optional caption used when this item is posted from the queue.":
        "Προαιρετική λεζάντα που χρησιμοποιείται όταν το στοιχείο δημοσιεύεται από την ουρά.",
    "Include in the automatic content queue.": "Συμπερίληψη στην αυτόματη ουρά περιεχομένου.",

    # --- Recurring ---
    "Recurring posts": "Επαναλαμβανόμενες αναρτήσεις",
    "Posts that repeat every week, like the class timetable or a weekend reminder.":
        "Αναρτήσεις που επαναλαμβάνονται κάθε εβδομάδα, όπως το πρόγραμμα μαθημάτων ή μια υπενθύμιση για το Σαββατοκύριακο.",
    "+ New recurring post": "+ Νέα επαναλαμβανόμενη ανάρτηση",
    "New recurring post": "Νέα επαναλαμβανόμενη ανάρτηση",
    "AI caption": "Λεζάντα AI",
    "No recurring posts yet.": "Δεν υπάρχουν επαναλαμβανόμενες αναρτήσεις ακόμη.",
    "For you only, e.g. “Weekly timetable”.": "Μόνο για εσάς, π.χ. «Εβδομαδιαίο πρόγραμμα».",
    "The same media is used every time. Upload new files in the Library.":
        "Χρησιμοποιούνται κάθε φορά τα ίδια αρχεία. Ανεβάστε νέα αρχεία στη Βιβλιοθήκη.",
    "Your library is empty.": "Η βιβλιοθήκη σας είναι άδεια.",
    "Upload files first": "Ανεβάστε πρώτα αρχεία",
    "AI brief": "Οδηγία για το AI",
    "If AI fails, the caption above is used.": "Αν το AI αποτύχει, χρησιμοποιείται η παραπάνω λεζάντα.",
    "Delete this recurring post?": "Διαγραφή αυτής της επαναλαμβανόμενης ανάρτησης;",
    "Placeholders: {date}, {weekday}, {studio}. Ignored when an AI caption is generated.":
        "Μεταβλητές: {date}, {weekday}, {studio}. Αγνοείται όταν δημιουργείται λεζάντα με AI.",
    "Write a fresh caption with AI each time.": "Νέα λεζάντα με AI κάθε φορά.",
    "What the AI caption should be about.": "Για τι να γράφει η λεζάντα του AI.",
    "Optional link added to the end of the caption.": "Προαιρετικός σύνδεσμος στο τέλος της λεζάντας.",
    "Comma separated, 0=Mon … 6=Sun": "Χωρισμένα με κόμμα, 0=Δευ … 6=Κυρ",
    "Comma separated HH:MM, e.g. 09:00,18:30": "Χωρισμένες με κόμμα ΩΩ:ΛΛ, π.χ. 09:00,18:30",
    "24h times, comma separated, e.g. 09:00, 18:30": "Ώρες σε 24ωρη μορφή, χωρισμένες με κόμμα, π.χ. 09:00, 18:30",
    "Use HH:MM, e.g. 09:00, 18:30": "Χρησιμοποιήστε ΩΩ:ΛΛ, π.χ. 09:00, 18:30",
    "Add at least one time.": "Προσθέστε τουλάχιστον μία ώρα.",
    "Describe what the AI should write about.": "Περιγράψτε για τι να γράψει το AI.",

    # --- Queue ---
    "Keeps your feed active: on the days and times below, a photo or video is posted automatically, in order or at random. Photos become photo posts and videos become Reels.":
        "Κρατά το προφίλ σας ενεργό: τις ημέρες και ώρες παρακάτω δημοσιεύεται αυτόματα μια φωτογραφία ή ένα βίντεο, "
        "με τη σειρά ή τυχαία. Οι φωτογραφίες γίνονται αναρτήσεις φωτογραφίας και τα βίντεο Reels.",
    "Only an owner can change these settings.": "Μόνο ένας ιδιοκτήτης μπορεί να αλλάξει αυτές τις ρυθμίσεις.",
    "Queue is on": "Η ουρά είναι ενεργή",
    "Every posting day gets new random times inside this window, spread out so posts don't bunch together.":
        "Κάθε ημέρα δημοσίευσης παίρνει νέες τυχαίες ώρες μέσα σε αυτό το διάστημα, μοιρασμένες ώστε να μη μαζεύονται οι αναρτήσεις.",
    "AI isn't set up, so the default caption is used when an item has none.":
        "Το AI δεν έχει ρυθμιστεί, οπότε χρησιμοποιείται η προεπιλεγμένη λεζάντα όταν ένα στοιχείο δεν έχει.",
    "General context for AI-written queue captions.": "Γενικές πληροφορίες για τις λεζάντες της ουράς που γράφει το AI.",
    "Default caption": "Προεπιλεγμένη λεζάντα",
    "Used when an item has no caption and AI is off or fails.":
        "Χρησιμοποιείται όταν ένα στοιχείο δεν έχει λεζάντα και το AI είναι ανενεργό ή αποτυγχάνει.",
    "Library items still to post": "Στοιχεία βιβλιοθήκης που δεν έχουν δημοσιευτεί",
    "In the queue": "Στην ουρά",
    "One of these is picked at random each time.": "Κάθε φορά επιλέγεται τυχαία ένα από αυτά.",
    "Posted in this order.": "Δημοσιεύονται με αυτή τη σειρά.",
    "Add items from the Library with “+ Queue”.": "Προσθέστε στοιχεία από τη Βιβλιοθήκη με «+ Ουρά».",
    "(caption written automatically)": "(η λεζάντα γράφεται αυτόματα)",
    "The queue is empty.": "Η ουρά είναι άδεια.",
    "Item's own caption, otherwise AI": "Η λεζάντα του στοιχείου, αλλιώς AI",
    "Always AI": "Πάντα AI",
    "Item's own caption, otherwise the default caption": "Η λεζάντα του στοιχείου, αλλιώς η προεπιλεγμένη",
    "Only items I marked “In queue”": "Μόνο όσα σημείωσα «Στην ουρά»",
    "Anything in the library": "Οτιδήποτε στη βιβλιοθήκη",
    "At fixed times": "Σε σταθερές ώρες",
    "🎲 At random times, different every day": "🎲 Σε τυχαίες ώρες, διαφορετικές κάθε μέρα",
    "First post not before": "Πρώτη ανάρτηση όχι πριν από",
    "Last post not after": "Τελευταία ανάρτηση όχι μετά από",
    "Posts per day": "Αναρτήσεις την ημέρα",
    "Post from": "Δημοσίευση από",
    "Pick items at random instead of oldest first.": "Τυχαία επιλογή στοιχείων αντί για τα παλαιότερα πρώτα.",
    "Optional link added to the end of every queue caption.":
        "Προαιρετικός σύνδεσμος στο τέλος κάθε λεζάντας της ουράς.",
    "Post queue items as Stories instead of feed posts/Reels.":
        "Δημοσίευση των στοιχείων της ουράς ως Stories αντί για αναρτήσεις/Reels.",
    "When every item has been posted, start again from the least used.":
        "Όταν δημοσιευτούν όλα, ξεκίνα ξανά από τα λιγότερο χρησιμοποιημένα.",
    "%(count)s× a day at random times between %(start)s and %(end)s":
        "%(count)s× την ημέρα σε τυχαίες ώρες μεταξύ %(start)s και %(end)s",
    "The last time must be later than the first.": "Η τελευταία ώρα πρέπει να είναι μετά την πρώτη.",
    "Choose between 1 and 25 posts a day.": "Επιλέξτε από 1 έως 25 αναρτήσεις την ημέρα.",
    "That's too many for this window. Allow at least 15 minutes per post (max %(max)s here).":
        "Είναι πολλές για αυτό το διάστημα. Αφήστε τουλάχιστον 15 λεπτά ανά ανάρτηση (έως %(max)s εδώ).",

    # --- Links page ---
    "Instagram only allows one clickable link: the one in your bio. Put this page there, and every post's link is two taps away.":
        "Το Instagram επιτρέπει μόνο έναν σύνδεσμο που πατιέται: αυτόν στο βιογραφικό σας. Βάλτε εκεί αυτή τη σελίδα "
        "και ο σύνδεσμος κάθε ανάρτησης θα είναι δύο πατήματα μακριά.",
    "Open page ↗": "Άνοιγμα σελίδας ↗",
    "Your page address": "Η διεύθυνση της σελίδας σας",
    "In the Instagram app: Edit profile → Links → Add external link, paste it, and save. Then write “🔗 Link in bio” in posts that have a link.":
        "Στην εφαρμογή Instagram: Επεξεργασία προφίλ → Σύνδεσμοι → Προσθήκη εξωτερικού συνδέσμου, επικολλήστε τον "
        "και αποθηκεύστε. Μετά γράψτε «🔗 Σύνδεσμος στο bio» στις αναρτήσεις που έχουν σύνδεσμο.",
    "Buttons": "Κουμπιά",
    "E.g. “📝 Sign up for a class” → lineofdance.gr/epikoinonia.php. The first button is highlighted.":
        "Π.χ. «📝 Εγγραφή σε τμήμα» → lineofdance.gr/epikoinonia.php. Το πρώτο κουμπί τονίζεται.",
    "Published posts with a link right now: %(n)s": "Δημοσιευμένες αναρτήσεις με σύνδεσμο αυτή τη στιγμή: %(n)s",
    "Title": "Τίτλος",
    "Short text": "Σύντομο κείμενο",
    "Show my latest posts that have a link": "Εμφάνιση των τελευταίων αναρτήσεών μου που έχουν σύνδεσμο",
    "Button text": "Κείμενο κουμπιού",
    "Link, e.g. lineofdance.gr": "Σύνδεσμος, π.χ. lineofdance.gr",
    "Add the link for this button.": "Προσθέστε τον σύνδεσμο για αυτό το κουμπί.",
    "A link can't contain spaces.": "Ένας σύνδεσμος δεν μπορεί να έχει κενά.",
    "Links page saved.": "Η σελίδα συνδέσμων αποθηκεύτηκε.",
    "Tap a post to open its link": "Πατήστε μια ανάρτηση για να ανοίξει ο σύνδεσμός της",
    "The part of the link after “#” was removed, because Instagram turns it into a hashtag.":
        "Το τμήμα του συνδέσμου μετά το «#» αφαιρέθηκε, γιατί το Instagram το κάνει hashtag.",

    # --- Stats ---
    "How your posts do, and the best time to post.": "Πώς πάνε οι αναρτήσεις σας και ποια είναι η καλύτερη ώρα για δημοσίευση.",
    "Updated %(ago)s ago.": "Ενημερώθηκε πριν από %(ago)s.",
    "Refresh now": "Ανανέωση τώρα",
    "Connect Instagram first to see results.": "Συνδέστε πρώτα το Instagram για να δείτε αποτελέσματα.",
    "Followers": "Ακόλουθοι",
    "Posts analysed": "Αναρτήσεις που αναλύθηκαν",
    "Average people reached": "Μέση προσέγγιση (άτομα)",
    "Average engagement": "Μέση αλληλεπίδραση",
    "likes, comments, saves & shares per person reached": "likes, σχόλια, αποθηκεύσεις & κοινοποιήσεις ανά άτομο που είδε την ανάρτηση",
    "Best time to post": "Καλύτερη ώρα για δημοσίευση",
    "Between <b>%(start)s:00 and %(end)s:00</b>": "Μεταξύ <b>%(start)s:00 και %(end)s:00</b>",
    "when most of your followers are online": "όταν είναι online οι περισσότεροι ακόλουθοί σας",
    "when your posts have done best so far": "όταν οι αναρτήσεις σας έχουν πάει καλύτερα μέχρι τώρα",
    "Post my queue at random times in this window": "Δημοσίευση της ουράς σε τυχαίες ώρες μέσα σε αυτό το διάστημα",
    "Not enough posts yet to tell. After about 5 posts at different times of day, Postmanager will suggest the best hours. Random posting times help it learn faster.":
        "Δεν υπάρχουν ακόμη αρκετές αναρτήσεις. Μετά από περίπου 5 αναρτήσεις σε διαφορετικές ώρες, το Postmanager θα "
        "προτείνει τις καλύτερες ώρες. Οι τυχαίες ώρες δημοσίευσης το βοηθούν να μάθει πιο γρήγορα.",
    "Followers online by hour": "Ακόλουθοι online ανά ώρα",
    "Followers online (30-day total)": "Ακόλουθοι online (σύνολο 30 ημερών)",
    "Engagement by hour posted": "Αλληλεπίδραση ανά ώρα δημοσίευσης",
    "Interactions by hour posted": "Αλληλεπιδράσεις ανά ώρα δημοσίευσης",
    "Average engagement of posts published at each hour.": "Μέση αλληλεπίδραση των αναρτήσεων που δημοσιεύτηκαν σε κάθε ώρα.",
    "Average likes + comments + saves + shares of posts published at each hour.":
        "Μέσος όρος likes + σχολίων + αποθηκεύσεων + κοινοποιήσεων των αναρτήσεων κάθε ώρας.",
    "Highlighted: the best window.": "Τονισμένο: το καλύτερο διάστημα.",
    "Engagement by hour": "Αλληλεπίδραση ανά ώρα",
    "Engagement by day": "Αλληλεπίδραση ανά ημέρα",
    "Interactions by hour": "Αλληλεπιδράσεις ανά ώρα",
    "Interactions by day": "Αλληλεπιδράσεις ανά ημέρα",
    "Average interactions": "Μέσες αλληλεπιδράσεις",
    "By day of the week": "Ανά ημέρα της εβδομάδας",
    "Best posts": "Οι καλύτερες αναρτήσεις",
    "Posted": "Δημοσίευση",
    "Reached": "Προσέγγιση",
    "Engagement": "Αλληλεπίδραση",
    "❤️ likes · 💬 comments · 🔖 saves · ↗️ shares": "❤️ likes · 💬 σχόλια · 🔖 αποθηκεύσεις · ↗️ κοινοποιήσεις",
    "No results yet. Click “Refresh now”.": "Δεν υπάρχουν αποτελέσματα ακόμη. Πατήστε «Ανανέωση τώρα».",
    "no data": "χωρίς δεδομένα",
    "no posts": "καμία ανάρτηση",
    "posts: %(n)s": "αναρτήσεις: %(n)s",
    "Show as table": "Εμφάνιση ως πίνακας",
    "Results updated from Instagram.": "Τα αποτελέσματα ενημερώθηκαν από το Instagram.",
    "The queue now posts at random times between %(start)s and %(end)s.":
        "Η ουρά δημοσιεύει πλέον σε τυχαίες ώρες μεταξύ %(start)s και %(end)s.",
    "Postmanager doesn't have permission to read your post results yet. In your Meta app open Instagram → Permissions and features, add “instagram_business_manage_insights”, then generate a new access token and paste it on the Instagram page.":
        "Το Postmanager δεν έχει ακόμη άδεια να διαβάζει τα αποτελέσματα των αναρτήσεών σας. Στην εφαρμογή Meta ανοίξτε "
        "Instagram → Permissions and features, προσθέστε το «instagram_business_manage_insights», δημιουργήστε νέο "
        "access token και επικολλήστε το στη σελίδα Instagram.",
    "Instagram didn't return results right now: %(error)s": "Το Instagram δεν έδωσε αποτελέσματα αυτή τη στιγμή: %(error)s",

    # --- Instagram page ---
    "Postmanager is connected and can publish for you.": "Το Postmanager είναι συνδεδεμένο και μπορεί να δημοσιεύει για εσάς.",
    "Connect the studio's Instagram once, and Postmanager can publish for you.":
        "Συνδέστε μία φορά το Instagram της σχολής και το Postmanager θα δημοσιεύει για εσάς.",
    "Connected": "Συνδεδεμένο",
    "Connected %(date)s · renews automatically": "Συνδέθηκε %(date)s · ανανεώνεται αυτόματα",
    "(valid until %(date)s)": "(ισχύει έως %(date)s)",
    "Check connection": "Έλεγχος σύνδεσης",
    "Connect a different account": "Σύνδεση άλλου λογαριασμού",
    "Disconnect": "Αποσύνδεση",
    "Disconnect Instagram? Scheduled posts will fail until you reconnect.":
        "Αποσύνδεση του Instagram; Οι προγραμματισμένες αναρτήσεις θα αποτυγχάνουν μέχρι να συνδεθείτε ξανά.",
    "This copy of the app runs on your computer. Connecting works, but Instagram can only fetch photos from the online version.":
        "Αυτό το αντίγραφο της εφαρμογής τρέχει στον υπολογιστή σας. Η σύνδεση λειτουργεί, αλλά το Instagram μπορεί να "
        "πάρει φωτογραφίες μόνο από την online έκδοση.",
    "Make sure it's a professional account": "Βεβαιωθείτε ότι είναι επαγγελματικός λογαριασμός",
    "Instagram only lets apps post to Business or Creator accounts (free, and nothing changes for your followers).":
        "Το Instagram επιτρέπει σε εφαρμογές να δημοσιεύουν μόνο σε λογαριασμούς Επιχείρησης ή Δημιουργού "
        "(δωρεάν, και τίποτα δεν αλλάζει για τους ακολούθους σας).",
    "In the Instagram app: Profile → ☰ → Settings → Account type and tools → Switch to professional account → Business. Skip this if it already is.":
        "Στην εφαρμογή Instagram: Προφίλ → ☰ → Ρυθμίσεις → Τύπος λογαριασμού και εργαλεία → Αλλαγή σε επαγγελματικό "
        "λογαριασμό → Επιχείρηση. Παραλείψτε το αν είναι ήδη.",
    "Create a free Meta app": "Δημιουργήστε μια δωρεάν εφαρμογή Meta",
    "(one time, ~3 min)": "(μία φορά, ~3 λεπτά)",
    "Instagram requires every posting tool to have one. Log in with the Facebook account that manages the studio's Instagram.":
        "Το Instagram το απαιτεί για κάθε εργαλείο δημοσίευσης. Συνδεθείτε με τον λογαριασμό Facebook που διαχειρίζεται "
        "το Instagram της σχολής.",
    "Open Meta for Developers ↗": "Άνοιγμα Meta for Developers ↗",
    "App name:": "Όνομα εφαρμογής:",
    "Use case:": "Περίπτωση χρήσης:",
    "Business:": "Επιχείρηση:",
    "Get the connection key": "Πάρτε το κλειδί σύνδεσης",
    "In your new app, open Instagram (left menu) → API setup with Instagram login.":
        "Στη νέα σας εφαρμογή ανοίξτε Instagram (αριστερό μενού) → API setup with Instagram login.",
    "Under “1. Generate access tokens” click Add account and log in with the studio's Instagram. Allow everything it asks.":
        "Στο «1. Generate access tokens» πατήστε Add account και συνδεθείτε με το Instagram της σχολής. "
        "Επιτρέψτε ό,τι ζητήσει.",
    "Click Generate token next to the account, tick the box, and Copy the long code (starts with IG).":
        "Πατήστε Generate token δίπλα στον λογαριασμό, τσεκάρετε το κουτάκι και αντιγράψτε τον μεγάλο κωδικό "
        "(ξεκινά με IG).",
    "If Meta says the account must accept an invite: Instagram app → Settings → Website permissions → Apps and websites → Tester invites → Accept, then try again.":
        "Αν η Meta πει ότι ο λογαριασμός πρέπει να αποδεχτεί πρόσκληση: εφαρμογή Instagram → Ρυθμίσεις → Άδειες "
        "ιστοτόπων → Εφαρμογές και ιστότοποι → Προσκλήσεις δοκιμαστών → Αποδοχή, και δοκιμάστε ξανά.",
    "Paste it here": "Επικολλήστε το εδώ",
    "Postmanager checks the key, then keeps it renewed for you automatically.":
        "Το Postmanager ελέγχει το κλειδί και το ανανεώνει αυτόματα για εσάς.",
    "Connect Instagram": "Σύνδεση Instagram",
    "Alternative: a “Log in with Instagram” button": "Εναλλακτικά: κουμπί «Σύνδεση με Instagram»",
    "(optional, for reconnecting without copying keys)": "(προαιρετικό, για επανασύνδεση χωρίς αντιγραφή κλειδιών)",
    "Log in with Instagram": "Σύνδεση με Instagram",
    "To change the app keys, save new ones below.": "Για αλλαγή των κλειδιών της εφαρμογής, αποθηκεύστε νέα παρακάτω.",
    "In the Meta app: Instagram → API setup with Instagram login → 3. Set up Instagram business login → Business login settings.":
        "Στην εφαρμογή Meta: Instagram → API setup with Instagram login → 3. Set up Instagram business login → "
        "Business login settings.",
    "Add this OAuth redirect URI and save:": "Προσθέστε αυτό το OAuth redirect URI και αποθηκεύστε:",
    "Copy the Instagram app ID and Instagram app secret from the top of that page into the form below.":
        "Αντιγράψτε το Instagram app ID και το Instagram app secret από την κορυφή εκείνης της σελίδας στη φόρμα παρακάτω.",
    "Save app keys": "Αποθήκευση κλειδιών εφαρμογής",
    "Access token": "Access token",
    "Instagram app ID": "Instagram app ID",
    "Instagram app secret": "Instagram app secret",
    "Leave empty to keep the saved secret.": "Αφήστε το κενό για να κρατήσετε το αποθηκευμένο secret.",
    "Enter the app secret.": "Συμπληρώστε το app secret.",
    "Saved. You can now use “Log in with Instagram”.": "Αποθηκεύτηκε. Μπορείτε πλέον να χρησιμοποιείτε το «Σύνδεση με Instagram».",
    "Couldn't connect: %(error)s": "Η σύνδεση απέτυχε: %(error)s",
    "🎉 Connected to Instagram as %(account)s.": "🎉 Συνδεθήκατε στο Instagram ως %(account)s.",
    "The connection isn't working: %(error)s": "Η σύνδεση δεν λειτουργεί: %(error)s",
    "✅ Connection works: posting as @%(username)s.": "✅ Η σύνδεση λειτουργεί: δημοσίευση ως @%(username)s.",
    "%(used)s of %(limit)s daily posts used.": "Χρησιμοποιήθηκαν %(used)s από %(limit)s ημερήσιες αναρτήσεις.",
    "Instagram connection cancelled: %(reason)s": "Η σύνδεση με το Instagram ακυρώθηκε: %(reason)s",
    "The connection request expired. Please try again.": "Το αίτημα σύνδεσης έληξε. Δοκιμάστε ξανά.",
    "Instagram disconnected. Scheduled posts will fail until you reconnect.":
        "Το Instagram αποσυνδέθηκε. Οι προγραμματισμένες αναρτήσεις θα αποτυγχάνουν μέχρι να συνδεθείτε ξανά.",

    # --- Instagram errors ---
    "Instagram didn't grant permission to publish. When generating the token, allow all requested permissions.":
        "Το Instagram δεν έδωσε άδεια δημοσίευσης. Όταν δημιουργείτε το token, επιτρέψτε όλες τις άδειες που ζητούνται.",
    "The Instagram connection key is invalid or has expired. Generate a new one in the Meta app (Instagram → API setup → Generate access tokens) and paste it on the Instagram page.":
        "Το κλειδί σύνδεσης Instagram δεν είναι έγκυρο ή έχει λήξει. Δημιουργήστε νέο στην εφαρμογή Meta "
        "(Instagram → API setup → Generate access tokens) και επικολλήστε το στη σελίδα Instagram.",
    "Instagram's limit of 100 posts per 24 hours was reached. Try again later.":
        "Συμπληρώθηκε το όριο του Instagram των 100 αναρτήσεων ανά 24 ώρες. Δοκιμάστε αργότερα.",
    "Instagram is rate-limiting requests right now. It will retry automatically.":
        "Το Instagram περιορίζει προσωρινά τα αιτήματα. Θα γίνει αυτόματα νέα προσπάθεια.",
    "Instagram returned an unexpected response (HTTP %(status)s).": "Το Instagram έδωσε απρόσμενη απάντηση (HTTP %(status)s).",
    "%(explanation)s (Instagram said: %(message)s)": "%(explanation)s (Μήνυμα Instagram: %(message)s)",
    "That doesn't look like an access token. It's a long code starting with “IG”.":
        "Αυτό δεν μοιάζει με access token. Είναι ένας μεγάλος κωδικός που ξεκινά με «IG».",
    "@%(username)s is a personal account. Instagram only allows apps to post to professional accounts: in the Instagram app go to Settings → Account type and tools → Switch to professional account (free), then generate a new token.":
        "Ο @%(username)s είναι προσωπικός λογαριασμός. Το Instagram επιτρέπει σε εφαρμογές να δημοσιεύουν μόνο σε "
        "επαγγελματικούς λογαριασμούς: στην εφαρμογή Instagram πηγαίνετε Ρυθμίσεις → Τύπος λογαριασμού και εργαλεία → "
        "Αλλαγή σε επαγγελματικό λογαριασμό (δωρεάν) και δημιουργήστε νέο token.",
    "Instagram could not process the media: %(status)s": "Το Instagram δεν μπόρεσε να επεξεργαστεί το αρχείο: %(status)s",
    "Add at least one photo or video.": "Προσθέστε τουλάχιστον μία φωτογραφία ή ένα βίντεο.",
    "A photo post needs exactly one photo (use Reel for a video, Carousel for several).":
        "Μια ανάρτηση φωτογραφίας χρειάζεται ακριβώς μία φωτογραφία (Reel για βίντεο, Καρουζέλ για πολλές).",
    "A carousel needs between 2 and 10 photos/videos.": "Ένα καρουζέλ χρειάζεται από 2 έως 10 φωτογραφίες/βίντεο.",
    "A Reel needs exactly one video.": "Ένα Reel χρειάζεται ακριβώς ένα βίντεο.",
    "A Story needs exactly one photo or video.": "Ένα Story χρειάζεται ακριβώς μία φωτογραφία ή ένα βίντεο.",
    "Instagram captions (including the link) are limited to 2,200 characters.":
        "Οι λεζάντες του Instagram (μαζί με τον σύνδεσμο) έχουν όριο 2.200 χαρακτήρες.",
    "Instagram allows at most 30 hashtags.": "Το Instagram επιτρέπει έως 30 hashtags.",
    "No Instagram account is connected.": "Δεν έχει συνδεθεί λογαριασμός Instagram.",

    # --- Post messages ---
    "Only an owner can do that.": "Μόνο ένας ιδιοκτήτης μπορεί να το κάνει αυτό.",
    "This post is already published and can't be edited.": "Αυτή η ανάρτηση έχει ήδη δημοσιευτεί και δεν μπορεί να αλλάξει.",
    "Scheduled for %(when)s.": "Προγραμματίστηκε για %(when)s.",
    "Heads-up: automatic publishing isn't running right now, so this post won't go out on time. An owner needs to set up the timer (see the banner).":
        "Προσοχή: η αυτόματη δημοσίευση δεν λειτουργεί αυτή τη στιγμή, οπότε η ανάρτηση δεν θα βγει στην ώρα της. "
        "Ένας ιδιοκτήτης πρέπει να ρυθμίσει το χρονόμετρο (δείτε την ειδοποίηση).",
    "Draft saved.": "Το πρόχειρο αποθηκεύτηκε.",
    "Publishing now. It will appear on Instagram within a minute or two.":
        "Δημοσιεύεται τώρα. Θα εμφανιστεί στο Instagram σε ένα-δύο λεπτά.",
    "Published to Instagram! 🎉": "Δημοσιεύτηκε στο Instagram! 🎉",
    "Publishing failed: %(error)s": "Η δημοσίευση απέτυχε: %(error)s",
    "Instagram is still processing this post. It will go live within a few minutes.":
        "Το Instagram επεξεργάζεται ακόμη την ανάρτηση. Θα δημοσιευτεί σε λίγα λεπτά.",
    "This post is publishing right now; try again in a minute.": "Η ανάρτηση δημοσιεύεται αυτή τη στιγμή· δοκιμάστε σε ένα λεπτό.",
    "Post removed from Postmanager.": "Η ανάρτηση αφαιρέθηκε από το Postmanager.",
    "Post removed from Postmanager. It is still on Instagram.":
        "Η ανάρτηση αφαιρέθηκε από το Postmanager. Παραμένει στο Instagram.",
    "Copied as a new draft.": "Αντιγράφηκε ως νέο πρόχειρο.",
    "Saved. Next post: %(when)s.": "Αποθηκεύτηκε. Επόμενη ανάρτηση: %(when)s.",
    "Recurring post deleted.": "Η επαναλαμβανόμενη ανάρτηση διαγράφηκε.",
    "Only an owner can change the queue settings.": "Μόνο ένας ιδιοκτήτης μπορεί να αλλάξει τις ρυθμίσεις της ουράς.",
    "Saved. The queue is off. Tick “Queue is on” to start posting.":
        "Αποθηκεύτηκε. Η ουρά είναι ανενεργή. Τσεκάρετε «Η ουρά είναι ενεργή» για να ξεκινήσουν οι αναρτήσεις.",
    "Saved, but no posting time could be planned. Check the days and times.":
        "Αποθηκεύτηκε, αλλά δεν προγραμματίστηκε ώρα δημοσίευσης. Ελέγξτε τις ημέρες και τις ώρες.",
    "✅ Queue is on. Next post: %(when)s.": "✅ Η ουρά είναι ενεργή. Επόμενη ανάρτηση: %(when)s.",
    "There's nothing to post yet. Upload photos or choose “Anything in the library”.":
        "Δεν υπάρχει τίποτα για δημοσίευση ακόμη. Ανεβάστε φωτογραφίες ή επιλέξτε «Οτιδήποτε στη βιβλιοθήκη».",
    "Describe the post or select some media first.": "Περιγράψτε την ανάρτηση ή επιλέξτε πρώτα κάποια αρχεία.",

    # --- Uploads ---
    "Uploads aren't possible yet: connect Blob storage to the Vercel project, then redeploy.":
        "Το ανέβασμα δεν είναι ακόμη δυνατό: συνδέστε αποθήκευση Blob στο έργο Vercel και κάντε νέο deploy.",
    "Uploaded %(count)s file(s).": "Ανέβηκαν %(count)s αρχεία.",
    "Uploaded %(n)s file(s).": "Ανέβηκαν %(n)s αρχεία.",
    "Direct uploads are not enabled.": "Το απευθείας ανέβασμα δεν είναι ενεργό.",
    "This file is used by a post. Delete the post first.": "Το αρχείο χρησιμοποιείται σε ανάρτηση. Διαγράψτε πρώτα την ανάρτηση.",
    "File deleted.": "Το αρχείο διαγράφηκε.",
    "%(name)s: only photos and MP4/MOV videos are supported.": "%(name)s: υποστηρίζονται μόνο φωτογραφίες και βίντεο MP4/MOV.",
    "%(name)s: this file couldn't be opened as a photo. Try exporting it as JPEG.":
        "%(name)s: το αρχείο δεν ανοίγει ως φωτογραφία. Δοκιμάστε να το αποθηκεύσετε ως JPEG.",
    "%(name)s: videos can be at most 300 MB.": "%(name)s: τα βίντεο μπορούν να είναι έως 300 MB.",
    "%(name)s: photos can be at most 40 MB.": "%(name)s: οι φωτογραφίες μπορούν να είναι έως 40 MB.",
    "%(name)s: the upload didn't arrive. Please try again.": "%(name)s: το αρχείο δεν έφτασε. Δοκιμάστε ξανά.",
    "Unknown upload.": "Άγνωστο αρχείο.",
    "Uploading %(i)s of %(n)s: %(name)s": "Ανέβασμα %(i)s από %(n)s: %(name)s",
    "Upload failed (%(status)s).": "Το ανέβασμα απέτυχε (%(status)s).",
    "Storage refused the upload (%(status)s).": "Η αποθήκευση απέρριψε το αρχείο (%(status)s).",
    "Network error while uploading.": "Σφάλμα δικτύου κατά το ανέβασμα.",

    # --- Page scripts ---
    "%(n)s selected": "%(n)s επιλεγμένα",
    "None selected": "Κανένα επιλεγμένο",
    "One photo. Photos that are too tall or wide get soft blurred borders automatically.":
        "Μία φωτογραφία. Όσες είναι πολύ ψηλές ή φαρδιές παίρνουν αυτόματα απαλό θολό περιθώριο.",
    "2–10 photos/videos. Click them in the order you want them to appear.":
        "2–10 φωτογραφίες/βίντεο. Πατήστε τα με τη σειρά που θέλετε να εμφανίζονται.",
    "One vertical video (MP4/MOV, 9:16 works best, 3 sec – 15 min).":
        "Ένα κάθετο βίντεο (MP4/MOV, ιδανικά 9:16, 3 δευτ. – 15 λεπτά).",
    "One photo or video. Stories have no caption and disappear after 24h.":
        "Μία φωτογραφία ή ένα βίντεο. Τα Stories δεν έχουν λεζάντα και εξαφανίζονται μετά από 24 ώρες.",
    "%(chars)s / 2200 characters · %(tags)s / 30 hashtags": "%(chars)s / 2200 χαρακτήρες · %(tags)s / 30 hashtags",
    "Publish this to Instagram now?": "Δημοσίευση στο Instagram τώρα;",
    "Writing…": "Γράφει…",
    "Use this caption": "Χρήση αυτής της λεζάντας",

    # --- AI ---
    "AI captions are not set up: add ANTHROPIC_API_KEY to the environment.":
        "Οι λεζάντες AI δεν έχουν ρυθμιστεί: προσθέστε το ANTHROPIC_API_KEY στις ρυθμίσεις.",
    "The Anthropic API key is invalid.": "Το κλειδί API της Anthropic δεν είναι έγκυρο.",
    "Too many AI requests right now; try again in a minute.": "Πάρα πολλά αιτήματα AI αυτή τη στιγμή· δοκιμάστε σε ένα λεπτό.",
    "AI service error (%(status)s).": "Σφάλμα υπηρεσίας AI (%(status)s).",
    "Could not reach the AI service.": "Δεν ήταν δυνατή η σύνδεση με την υπηρεσία AI.",
    "The AI declined to write a caption for this content.": "Το AI αρνήθηκε να γράψει λεζάντα για αυτό το περιεχόμενο.",
    "The AI response was cut off; try a shorter description.": "Η απάντηση του AI κόπηκε· δοκιμάστε πιο σύντομη περιγραφή.",
    "The AI returned an unexpected response.": "Το AI έδωσε απρόσμενη απάντηση.",
    "The AI returned no captions.": "Το AI δεν έδωσε λεζάντες.",

    # --- Team ---
    "Editors can create, schedule and publish posts and manage the library. Owners can also approve people, connect Instagram and change recurring posts and the queue.":
        "Οι συντάκτες δημιουργούν, προγραμματίζουν και δημοσιεύουν αναρτήσεις και διαχειρίζονται τη βιβλιοθήκη. "
        "Οι ιδιοκτήτες επιπλέον εγκρίνουν άτομα, συνδέουν το Instagram και αλλάζουν τις επαναλαμβανόμενες αναρτήσεις και την ουρά.",
    "Waiting for approval": "Σε αναμονή έγκρισης",
    "Signed up %(ago)s ago": "Εγγράφηκε πριν από %(ago)s",
    "with Google": "με Google",
    "Approve as editor": "Έγκριση ως συντάκτης",
    "Approve as owner": "Έγκριση ως ιδιοκτήτης",
    "Make this person an owner? Owners have full control.": "Να γίνει ιδιοκτήτης; Οι ιδιοκτήτες έχουν πλήρη έλεγχο.",
    "Decline": "Απόρριψη",
    "Decline this request?": "Απόρριψη αυτού του αιτήματος;",
    "Nobody is waiting. Share this sign-up link with your team:":
        "Κανείς δεν περιμένει. Μοιραστείτε αυτόν τον σύνδεσμο εγγραφής με την ομάδα σας:",
    "Members": "Μέλη",
    "Role": "Ρόλος",
    "Since": "Από",
    "Owner": "Ιδιοκτήτης",
    "Editor": "Συντάκτης",
    "Remove this person’s access?": "Αφαίρεση της πρόσβασης αυτού του ατόμου;",
    "You can't change your own access. Ask another owner.":
        "Δεν μπορείτε να αλλάξετε τη δική σας πρόσβαση. Ζητήστε το από άλλον ιδιοκτήτη.",
    "%(who)s can now use the app as %(role)s.": "Ο/Η %(who)s μπορεί πλέον να χρησιμοποιεί την εφαρμογή ως %(role)s.",
    "There must always be at least one owner.": "Πρέπει πάντα να υπάρχει τουλάχιστον ένας ιδιοκτήτης.",
    "%(who)s is now %(role)s.": "Ο/Η %(who)s είναι πλέον %(role)s.",
    "%(who)s no longer has access.": "Ο/Η %(who)s δεν έχει πλέον πρόσβαση.",
    "Declined %(who)s.": "Απορρίφθηκε: %(who)s.",
    "%(studio)s Posts: %(who)s wants access": "%(studio)s Posts: ο/η %(who)s ζητά πρόσβαση",
    "%(who)s (%(email)s) signed up and is waiting for approval.": "Ο/Η %(who)s (%(email)s) εγγράφηκε και περιμένει έγκριση.",
    "Approve or decline: %(url)s": "Έγκριση ή απόρριψη: %(url)s",

    # --- Pending ---
    "Almost there!": "Σχεδόν έτοιμο!",
    "Your account <b>%(email)s</b> has been created.": "Ο λογαριασμός σας <b>%(email)s</b> δημιουργήθηκε.",
    "An owner of %(studio)s needs to approve it before you can manage posts. They've been notified. This page will let you in once they have.":
        "Ένας ιδιοκτήτης του %(studio)s πρέπει να τον εγκρίνει πριν διαχειριστείτε αναρτήσεις. Έχει ειδοποιηθεί. "
        "Αυτή η σελίδα θα σας αφήσει να μπείτε μόλις εγκριθεί.",
    "Check again": "Έλεγχος ξανά",

    # --- Automatic publishing ---
    "Automatic publishing": "Αυτόματη δημοσίευση",
    "Scheduled, recurring and queued posts are published by a timer that visits a secret link every 5 minutes.":
        "Οι προγραμματισμένες, επαναλαμβανόμενες και αναρτήσεις ουράς δημοσιεύονται από ένα χρονόμετρο που επισκέπτεται "
        "έναν μυστικό σύνδεσμο κάθε 5 λεπτά.",
    "Not running": "Δεν λειτουργεί",
    "Last run %(ago)s ago (%(when)s).": "Τελευταία εκτέλεση πριν από %(ago)s (%(when)s).",
    "It has never run.": "Δεν έχει εκτελεστεί ποτέ.",
    "Until it's set up, posts only go out when you press “Publish now”.":
        "Μέχρι να ρυθμιστεί, οι αναρτήσεις βγαίνουν μόνο όταν πατάτε «Δημοσίευση τώρα».",
    "Running": "Λειτουργεί",
    "Last run %(ago)s ago. Scheduled posts go out within about 5 minutes of their time.":
        "Τελευταία εκτέλεση πριν από %(ago)s. Οι προγραμματισμένες αναρτήσεις βγαίνουν μέσα σε περίπου 5 λεπτά από την ώρα τους.",
    "Create a free cron-job.org account": "Δημιουργήστε δωρεάν λογαριασμό στο cron-job.org",
    "Open cron-job.org ↗": "Άνοιγμα cron-job.org ↗",
    "Create a cronjob": "Δημιουργήστε ένα cronjob",
    "Click “Create cronjob”. Title: Postmanager": "Πατήστε «Create cronjob». Τίτλος: Postmanager",
    "URL — paste this (keep it private):": "URL — επικολλήστε αυτό (κρατήστε το μυστικό):",
    "Execution schedule: every 5 minutes": "Execution schedule: κάθε 5 λεπτά",
    "Click “Create”.": "Πατήστε «Create».",
    "Check it": "Έλεγχος",
    "Reload this page in 5 minutes. It should say “✅ Running”.":
        "Ανανεώστε αυτή τη σελίδα σε 5 λεπτά. Θα πρέπει να γράφει «✅ Λειτουργεί».",
    "Set the CRON_SECRET setting first.": "Ορίστε πρώτα τη ρύθμιση CRON_SECRET.",

    # --- Sign in / sign up ---
    "Sign in": "Σύνδεση",
    "Sign in to manage Instagram posts": "Συνδεθείτε για να διαχειριστείτε τις αναρτήσεις Instagram",
    "Continue with Google": "Συνέχεια με Google",
    "Sign up with Google": "Εγγραφή με Google",
    "or with email": "ή με email",
    "Email": "Email",
    "Password": "Κωδικός",
    "Repeat password": "Επανάληψη κωδικού",
    "Forgot your password?": "Ξεχάσατε τον κωδικό σας;",
    "New here?": "Νέος/α εδώ;",
    "Create an account": "Δημιουργία λογαριασμού",
    "Create account": "Δημιουργία λογαριασμού",
    "Create your account": "Δημιουργήστε τον λογαριασμό σας",
    "An owner of %(studio)s will approve your access.": "Ένας ιδιοκτήτης του %(studio)s θα εγκρίνει την πρόσβασή σας.",
    "At least 8 characters, not too common.": "Τουλάχιστον 8 χαρακτήρες, όχι πολύ συνηθισμένος.",
    "Already have an account?": "Έχετε ήδη λογαριασμό;",
}
