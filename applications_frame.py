import os 
import re 
import tempfile 
import threading 
import tkinter as tk 
from tkinter import ttk 
import stat 

class ApplicationsFrame (ttk .Frame ):
    """
    Lists apps from /Applications or /var/jb/Applications on the connected device.
    Shows app folder names (e.g., FaceTime.app) with icons picked from common filenames in the app bundle.
    Icons checked in order: icon_144.png, icon_57.png, icon_72.png, icon_114.png. Fallback to local defapp.png.

    Expects get_connection callable returning an active Paramiko SSHClient.
    """

    ICON_CANDIDATES =[
    "icon_144.png",
    "icon_128.png",
    "icon_120.png",
    "icon_114.png",
    "icon_76.png",
    "icon_72.png",
    "icon_60.png",
    "icon_57.png",
    ]

    def __init__ (self ,parent ,get_connection ):
        super ().__init__ (parent )
        self .get_connection =get_connection 
        self ._tmpdir =tempfile .mkdtemp (prefix ="apps_icons_")
        self ._images ={}# keep references to photoimage
        self ._app_paths ={}
        self ._icon_cache ={}# app_path -> local icon path
        self ._loading =False 
        self ._load_id =0 
        # try to enable high-quality resize with pil
        try :
            from PIL import Image ,ImageTk # type: ignore
            self ._PIL =(Image ,ImageTk )
            # try to enable avif support if plugin is available
            try :
                import pillow_avif # type: ignore
            except Exception :
                pass 
        except Exception :
            self ._PIL =None 
        self ._build_ui ()
        # auto refresh on load
        self .after (100 ,self .refresh )

    def _build_ui (self ):
        toolbar =ttk .Frame (self )
        toolbar .pack (fill =tk .X ,padx =6 ,pady =6 )
        self .refresh_btn =ttk .Button (toolbar ,text ="Refresh",command =self .refresh )
        self .refresh_btn .pack (side =tk .LEFT )
        self .status =ttk .Label (toolbar ,text ="")
        self .status .pack (side =tk .LEFT ,padx =8 )

        # treeview with larger row height for 128px icons
        style =ttk .Style (self )
        try :
            style .configure ("Apps.Treeview",rowheight =132 )
        except Exception :
            pass 
        cols =("name",)
        self .tree =ttk .Treeview (self ,columns =cols ,show ="tree",style ="Apps.Treeview")
        self .tree .pack (fill =tk .BOTH ,expand =True )
        self .tree .bind ("<Double-1>",self ._on_open )
        try :
            self .tree .column ('#0',width =260 ,stretch =True )
        except Exception :
            pass 

        yscroll =ttk .Scrollbar (self ,orient =tk .VERTICAL ,command =self .tree .yview )
        self .tree .configure (yscrollcommand =yscroll .set )
        yscroll .place (in_ =self .tree ,relx =1.0 ,rely =0 ,relheight =1.0 ,anchor ="ne")

    def _set_status (self ,msg ):
        try :
            self .status .configure (text =msg )
        except Exception :
            pass 

    def refresh (self ):
        if self ._loading :
            return 
        self ._loading =True 
        self ._load_id +=1 
        load_id =self ._load_id 
        self ._set_status ("Connecting…")
        try :
            self .refresh_btn .configure (state =tk .DISABLED )
        except Exception :
            pass 
        self .tree .delete (*self .tree .get_children (""))
        self ._images .clear ()

        def worker ():
            client =None 
            sftp =None 
            try :
                try :
                    client =self .get_connection ()
                except Exception as e :
                    emsg =f"Connect failed: {e}"
                    self .after (0 ,lambda m =emsg :self ._set_status (m ))
                    return 
                try :
                    sftp =client .open_sftp ()
                except Exception as e :
                    emsg =f"SFTP failed: {e}"
                    self .after (0 ,lambda m =emsg :self ._set_status (m ))
                    return 
                dest ="/Applications"
                try :
                    sftp .stat ("/var/jb/Applications")
                    dest ="/var/jb/Applications"
                except Exception :
                    pass 
                self .after (0 ,lambda :self ._set_status (f"Listing {dest}…"))
                try :
                    entries =sftp .listdir_attr (dest )
                except Exception as e :
                    emsg =f"List failed: {e}"
                    self .after (0 ,lambda m =emsg :self ._set_status (m ))
                    return 
                apps =[]
                for ent in entries :
                    if not ent .filename .endswith ('.app'):
                        continue 
                    try :
                        if stat .S_ISDIR (ent .st_mode ):
                            apps .append (ent )
                    except Exception :
                    # as a fallback assume its a directory
                        apps .append (ent )
                apps .sort (key =lambda a :a .filename .lower ())

                total =len (apps )
                def insert_row (name ,app_path ,img_path ):
                    if load_id !=self ._load_id :
                        return 
                        # create photoimage on the ui thread only
                    img =self ._make_icon_from_local (img_path )if img_path else self ._default_icon ()
                    iid =self .tree .insert ("",tk .END ,text =name ,image =img )
                    self ._images [iid ]=img 
                    self ._app_paths [iid ]=app_path 
                for idx ,ent in enumerate (apps ,start =1 ):
                    if load_id !=self ._load_id :
                        break 
                    app_path =f"{dest}/{ent.filename}"
                    img_path =self ._find_icon_path (sftp ,app_path )
                    self .after (0 ,insert_row ,ent .filename ,app_path ,img_path )
                    if idx %5 ==0 or idx ==total :
                        self .after (0 ,lambda i =idx ,t =total :self ._set_status (f"Loaded {i}/{t} apps…"))
                self .after (0 ,lambda :self ._set_status (f"Loaded {total} apps."))
            finally :
                try :
                    sftp and sftp .close ()
                except Exception :
                    pass 
                try :
                    client and client .close ()
                except Exception :
                    pass 
                    # re-enable refresh on ui thread if this is the latest load
                def finish ():
                    if load_id ==self ._load_id :
                        self ._loading =False 
                        try :
                            self .refresh_btn .configure (state =tk .NORMAL )
                        except Exception :
                            pass 
                self .after (0 ,finish )

        threading .Thread (target =worker ,daemon =True ).start ()

    def _find_icon_path (self ,sftp ,app_path ):
        """Return a local file path for the best icon for this app, or a local fallback path if available. None if need to use generated placeholder."""
        # cache
        if app_path in self ._icon_cache and os .path .exists (self ._icon_cache [app_path ]):
            return self ._icon_cache [app_path ]
            # 1 try explicit candidate filenames
        for name in self .ICON_CANDIDATES :
            remote_file =f"{app_path}/{name}"
            try :
                sftp .stat (remote_file )
                path =self ._download_icon_to_local (sftp ,remote_file )
                if path :
                    self ._icon_cache [app_path ]=path 
                    return path 
            except Exception :
                pass 
                # 2 skip deep scan for speed fall back to local branding
                # 3 fallback to defappavif or defapppng in cwd or a generated placeholder
        fallback_avif =os .path .join (os .getcwd (),"defapp.avif")
        if os .path .exists (fallback_avif ):
            self ._icon_cache [app_path ]=fallback_avif 
            return fallback_avif 
        fallback =os .path .join (os .getcwd (),"defapp.png")
        if os .path .exists (fallback ):
            self ._icon_cache [app_path ]=fallback 
            return fallback 
            # final fallback: generated 128x128 placeholder
        return None 

    def _download_icon_to_local (self ,sftp ,remote_file ):
        local_file =os .path .join (
        self ._tmpdir ,
        os .path .basename (os .path .dirname (remote_file ))+"_"+os .path .basename (remote_file ),
        )
        try :
            sftp .get (remote_file ,local_file )
            return local_file 
        except Exception :
            return None 

    def _default_icon (self ,size :int =128 ):
        """Generate a neutral placeholder icon of given size."""
        if self ._PIL :
            Image ,ImageTk =self ._PIL 
            try :
                im =Image .new ('RGBA',(size ,size ),(200 ,200 ,200 ,255 ))
                return ImageTk .PhotoImage (im )
            except Exception :
                pass 
        try :
            img =tk .PhotoImage (width =size ,height =size )
            img .put ("#c8c8c8",to =(0 ,0 ,size ,size ))
            return img 
        except Exception :
            try :
                return tk .PhotoImage (width =32 ,height =32 )
            except Exception :
                return None 

    def _download_and_make_icon (self ,sftp ,remote_file ):
        local_file =os .path .join (self ._tmpdir ,os .path .basename (os .path .dirname (remote_file ))+"_"+os .path .basename (remote_file ))
        try :
            sftp .get (remote_file ,local_file )
        except Exception :
            return None 
        try :
            return self ._make_icon_from_local (local_file )
        except Exception :
            return None 

    def _make_icon_from_local (self ,local_file ,max_size =128 ):
    # use pil if available for high-quality resize fallback to tk subsample
        if self ._PIL :
            Image ,ImageTk =self ._PIL 
            try :
            # if its avif but pil doesnt have a decoder skip to fallback silently
                if local_file .lower ().endswith ('.avif'):
                    try :
                        exts =getattr (Image ,'registered_extensions',lambda :{})()
                        if '.avif'not in exts :
                            return None 
                    except Exception :
                        return None 
                im =Image .open (local_file ).convert ('RGBA')
                im .thumbnail ((max_size ,max_size ),Image .LANCZOS )
                return ImageTk .PhotoImage (im )
            except Exception :
                pass 
                # fallback: tk photoimage and subsample if needed
                # if trying to load avif without pil support skip and let caller fallback
        if local_file .lower ().endswith ('.avif'):
            return None 
        img =tk .PhotoImage (file =local_file )
        try :
            w =img .width ();h =img .height ()
            if w >max_size or h >max_size :
            # compute integer subsample factor
                factor =max (1 ,int (max (w /max_size ,h /max_size )))
                img =img .subsample (factor ,factor )
        except Exception :
            pass 
        return img 

    def _on_open (self ,event ):
    # double-click: attempt to launch the app on device by running its binary
        sel =self .tree .focus ()
        if not sel :
            return 
        app_name =self .tree .item (sel ,'text')
        app_path =self ._app_paths .get (sel )
        if not app_path :
            self ._set_status (app_name )
            return 
        self ._set_status (f"Launching {app_name}…")

        def worker ():
            client =None 
            try :
                try :
                    client =self .get_connection ()
                except Exception as e :
                    self .after (0 ,lambda :self ._set_status (f"Connect failed: {e}"))
                    return 
                sh =(
                "PLUTIL=$(command -v /var/jb/usr/bin/plutil || command -v /usr/bin/plutil); "
                f"PLIST=\"{app_path}/Info.plist\"; "
                f"APP=\"{app_path}\"; "
                # try cfbundleexecutable
                "EXE=$($PLUTIL -extract CFBundleExecutable raw -o - \"$PLIST\" 2>/dev/null); "
                "ELOW=; EUP=; if [ -n \"$EXE\" ]; then ELOW=$(printf %s \"$EXE\" | tr '[:upper:]' '[:lower:]'); EUP=$(printf %s \"$EXE\" | tr '[:lower:]' '[:upper:]'); fi; "
                # basename variants portable lower/upper using tr
                "BASE=$(basename \"$APP\"); BASE=${BASE%.app}; "
                "LOW=$(printf %s \"$BASE\" | tr '[:upper:]' '[:lower:]'); "
                "UP=$(printf %s \"$BASE\" | tr '[:lower:]' '[:upper:]'); "
                "CANDS=; [ -n \"$EXE\" ] && CANDS=\"$CANDS $EXE $ELOW $EUP\"; CANDS=\"$CANDS $BASE $LOW $UP\"; "
                "BIN=; for N in $CANDS; do if [ -e \"$APP/$N\" ]; then BIN=\"$APP/$N\"; break; fi; done; "
                # if still empty pick first executable file in app root
                "if [ -z \"$BIN\" ]; then for F in \"$APP\"/*; do [ -f \"$F\" ] && [ -x \"$F\" ] && { BIN=\"$F\"; break; }; done; fi; "
                # ensure executable bit and run as mobile in background with cwd=app
                "if [ -n \"$BIN\" ]; then chmod +x \"$BIN\" 2>/dev/null; fi; "
                "if [ -n \"$BIN\" ] && [ -x \"$BIN\" ]; then "
                "  su mobile -c \"sh -lc 'cd \"$APP\"; \"$BIN\" >/dev/null 2>&1 & echo started'\" >/dev/null 2>&1 || "
                "  sudo -u mobile sh -lc 'cd \"$APP\"; \"$BIN\" >/dev/null 2>&1 & echo started' >/dev/null 2>&1; "
                "  echo Launched: $BIN; "
                "else echo 'Could not launch binary (not found or not executable)'; fi"
                )
                stdin ,stdout ,stderr =client .exec_command (sh )
                out =stdout .read ().decode (errors ='ignore').strip ()
                err =stderr .read ().decode (errors ='ignore').strip ()
                msg =out or err or f"Tried launching {app_name}"
                self .after (0 ,lambda :self ._set_status (msg ))
            finally :
                try :
                    client and client .close ()
                except Exception :
                    pass 

        threading .Thread (target =worker ,daemon =True ).start ()
