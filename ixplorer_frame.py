import os 
import stat 
import threading 
import subprocess 
import shutil 
from datetime import datetime 

import tkinter as tk 
from tkinter import ttk ,filedialog ,messagebox 

try :
    import paramiko 
except Exception :
    paramiko =None 


class ExplorerFrame (ttk .Frame ):
    """
    Remote file explorer over SSH/SFTP.
    Expects:
      - get_connection: callable returning a connected paramiko.SSHClient
      - ip_var: tk.StringVar with current device IP (used for scp.exe)
    """

    def __init__ (self ,parent ,get_connection ,ip_var :tk .StringVar ):
        super ().__init__ (parent )
        self .get_connection =get_connection 
        self .ip_var =ip_var 

        self .current_path =tk .StringVar (value ="/")
        self .status_var =tk .StringVar (value ="Disconnected")
        self .progress_var =tk .DoubleVar (value =0.0 )
        self .use_scp =tk .BooleanVar (value =False )
        self .scp_path =tk .StringVar (value =self ._find_scp_path ())

        self ._client =None 
        self ._sftp =None 

        self ._build_ui ()
        self ._connect_and_list (initial =True )

        # ui
    def _build_ui (self ):
    # toolbar
        bar =ttk .Frame (self )
        bar .pack (fill =tk .X ,padx =8 ,pady =6 )
        ttk .Label (bar ,text ="Path:").pack (side =tk .LEFT )
        path_entry =ttk .Entry (bar ,textvariable =self .current_path ,width =60 )
        path_entry .pack (side =tk .LEFT ,padx =6 )
        path_entry .bind ('<Return>',lambda e :self ._list_dir ())
        ttk .Button (bar ,text ="Up",command =self ._go_up ).pack (side =tk .LEFT ,padx =4 )
        ttk .Button (bar ,text ="Refresh",command =self ._list_dir ).pack (side =tk .LEFT ,padx =4 )
        ttk .Button (bar ,text ="Connect",command =lambda :self ._connect_and_list (force =True )).pack (side =tk .LEFT ,padx =10 )

        # options
        opts =ttk .LabelFrame (self ,text ="Transfer Options")
        opts .pack (fill =tk .X ,padx =8 ,pady =4 )
        ttk .Checkbutton (opts ,text ="Use scp.exe when available (falls back to SFTP)",variable =self .use_scp ).pack (side =tk .LEFT ,padx =6 )
        ttk .Label (opts ,text ="scp.exe:").pack (side =tk .LEFT )
        scp_entry =ttk .Entry (opts ,textvariable =self .scp_path ,width =40 )
        scp_entry .pack (side =tk .LEFT ,padx =4 )
        ttk .Button (opts ,text ="Browse...",command =self ._choose_scp ).pack (side =tk .LEFT )

        # splitter: tree + actions
        mid =ttk .Frame (self )
        mid .pack (fill =tk .BOTH ,expand =True ,padx =8 ,pady =6 )

        columns =("display","size","modified","type")
        self .tree =ttk .Treeview (mid ,columns =columns ,show ='headings')
        self .tree .heading ('display',text ='Name')
        self .tree .column ('display',width =320 ,anchor =tk .W )
        self .tree .heading ('size',text ='Size')
        self .tree .column ('size',width =80 ,anchor =tk .E )
        self .tree .heading ('modified',text ='Modified')
        self .tree .column ('modified',width =160 ,anchor =tk .W )
        self .tree .heading ('type',text ='Type')
        self .tree .column ('type',width =90 ,anchor =tk .W )
        self .tree .pack (side =tk .LEFT ,fill =tk .BOTH ,expand =True )

        sb =ttk .Scrollbar (mid ,orient =tk .VERTICAL ,command =self .tree .yview )
        self .tree .configure (yscroll =sb .set )
        sb .pack (side =tk .LEFT ,fill =tk .Y )

        self .tree .bind ('<Double-1>',self ._on_double )

        # right actions
        actions =ttk .Frame (mid )
        actions .pack (side =tk .LEFT ,fill =tk .Y ,padx =6 )
        ttk .Button (actions ,text ="Upload...",command =self ._on_upload ).pack (fill =tk .X ,pady =2 )
        ttk .Button (actions ,text ="Download",command =self ._on_download ).pack (fill =tk .X ,pady =2 )
        ttk .Button (actions ,text ="Delete",command =self ._on_delete ).pack (fill =tk .X ,pady =2 )
        ttk .Button (actions ,text ="New Folder",command =self ._on_mkdir ).pack (fill =tk .X ,pady =2 )
        ttk .Button (actions ,text ="Rename",command =self ._on_rename ).pack (fill =tk .X ,pady =2 )

        # status
        status =ttk .Frame (self )
        status .pack (fill =tk .X ,padx =8 ,pady =6 )
        self .pbar =ttk .Progressbar (status ,variable =self .progress_var ,maximum =100 )
        self .pbar .pack (side =tk .LEFT ,fill =tk .X ,expand =True ,padx =6 )
        ttk .Label (status ,textvariable =self .status_var ).pack (side =tk .LEFT ,padx =6 )

        # helpers
    def _set_status (self ,text ):
        self .status_var .set (text )
        self .update_idletasks ()

    def _find_scp_path (self ):
    # try common locations or path
        for cand in [
        shutil .which ('scp'),
        r"C:\\Windows\\System32\\OpenSSH\\scp.exe",
        ]:
            if cand and os .path .isfile (cand ):
                return cand 
        return ""

    def _choose_scp (self ):
        path =filedialog .askopenfilename (title ="Select scp.exe",filetypes =[["scp.exe","scp.exe"],["All files","*.*"]])
        if path :
            self .scp_path .set (path )

    def _ensure_conn (self ):
        if self ._client and self ._sftp :
            return True 
        try :
            self ._client =self .get_connection ()
            self ._sftp =self ._client .open_sftp ()
            return True 
        except Exception as e :
            self ._set_status (f"Connect failed: {e}")
            return False 

    def _connect_and_list (self ,initial =False ,force =False ):
        def work ():
            if force :
                self ._close ()
            ok =self ._ensure_conn ()
            if ok :
                self ._set_status ("Connected")
                self ._list_dir ()
        threading .Thread (target =work ,daemon =True ).start ()

    def _close (self ):
        try :
            if self ._sftp :
                self ._sftp .close ()
        except Exception :
            pass 
        try :
            if self ._client :
                self ._client .close ()
        except Exception :
            pass 
        self ._sftp =None 
        self ._client =None 

    def _list_dir (self ):
        def work ():
            if not self ._ensure_conn ():
                return 
            path =self .current_path .get ()or '/'
            try :
                entries =self ._sftp .listdir_attr (path )
                rows =[]
                for e in entries :
                    mode =e .st_mode 
                    is_dir =stat .S_ISDIR (mode )
                    typ ='dir'if is_dir else 'file'
                    size =e .st_size if not is_dir else ''
                    mtime =datetime .fromtimestamp (e .st_mtime ).strftime ('%Y-%m-%d %H:%M')
                    icon =self ._icon_for (e .filename ,typ )
                    display =f"{icon} {e.filename}"
                    # keep both display string and real name
                    rows .append ((display ,size ,mtime ,typ ,e .filename ))
                    # sort by type dirs first then real name
                rows .sort (key =lambda r :(r [3 ]!='dir',r [4 ].lower ()))
                self ._populate_tree (rows )
                self ._set_status (f"Listed {path}")
            except Exception as e :
                self ._set_status (f"List failed: {e}")
        threading .Thread (target =work ,daemon =True ).start ()

    def _icon_for (self ,name :str ,typ :str )->str :
        if typ =='dir':
            return '📁'
        ext =os .path .splitext (name )[1 ].lower ()
        mapping ={
        '.ipa':'📦',
        '.deb':'📦',
        '.plist':'🧾',
        '.png':'🖼️',
        '.jpg':'🖼️',
        '.jpeg':'🖼️',
        '.heic':'🖼️',
        '.mov':'🎞️',
        '.mp4':'🎬',
        '.m4v':'🎬',
        '.sh':'🧩',
        '.py':'🐍',
        '.txt':'📄',
        '.log':'📝',
        '.dylib':'🧱',
        '.zip':'🗜️',
        '.tar':'🗜️',
        '.gz':'🗜️',
        '.7z':'🗜️',
        '.app':'📱',
        '.bundle':'🧩',
        }
        return mapping .get (ext ,'📄')

    def _populate_tree (self ,rows ):
        def ui ():
            self .tree .delete (*self .tree .get_children ())
            for display ,size ,mtime ,typ ,realname in rows :
            # store real filename in item text show icon+name in first column
                self .tree .insert ('',tk .END ,text =realname ,values =(display ,size ,mtime ,typ ))
        self .after (0 ,ui )

    def _on_double (self ,_ ):
        item =self .tree .focus ()
        if not item :
            return 
        vals =self .tree .item (item ,'values')
        typ =vals [3 ]if len (vals )>3 else 'file'
        name =self .tree .item (item ,'text')or ''
        if typ =='dir':
            newp =os .path .normpath (os .path .join (self .current_path .get ()or '/',name ))
            if not newp .startswith ('/'):
                newp ='/'+newp 
            self .current_path .set (newp )
            self ._list_dir ()

    def _go_up (self ):
        p =os .path .normpath (os .path .join (self .current_path .get ()or '/','..'))
        if not p .startswith ('/'):
            p ='/'
        self .current_path .set (p )
        self ._list_dir ()

        # actions
    def _on_upload (self ):
        files =filedialog .askopenfilenames (title ="Select files to upload")
        if not files :
            return 
        dest_dir =self .current_path .get ()or '/'
        self ._transfer_many (files ,dest_dir ,upload =True )

    def _on_download (self ):
        sel =self .tree .selection ()
        if not sel :
            messagebox .showinfo ("Download","Select file(s) to download.")
            return 
        local_dir =filedialog .askdirectory (title ="Select local folder")
        if not local_dir :
            return 
        items =[]
        for it in sel :
            vals =self .tree .item (it ,'values')
            typ =vals [3 ]if len (vals )>3 else 'file'
            name =self .tree .item (it ,'text')or ''
            if typ =='dir':
                messagebox .showwarning ("Download",f"Skipping folder: {name}")
                continue 
            items .append ((os .path .join (self .current_path .get ()or '/',name ),os .path .join (local_dir ,name )))
        if not items :
            return 
        self ._download_many (items )

    def _on_delete (self ):
        sel =self .tree .selection ()
        if not sel :
            return 
        names =[self .tree .item (it ,'text')or ''for it in sel ]
        if not messagebox .askyesno ("Delete",f"Delete {len(names)} item(s)?"):
            return 
        def work ():
            if not self ._ensure_conn ():
                return 
            base =self .current_path .get ()or '/'
            errs =[]
            for n in names :
                rp =os .path .join (base ,n )
                try :
                    st =self ._sftp .stat (rp )
                    if stat .S_ISDIR (st .st_mode ):
                        self ._rmdir_recursive (rp )
                    else :
                        self ._sftp .remove (rp )
                except Exception as e :
                    errs .append (f"{n}: {e}")
            self ._list_dir ()
            if errs :
                self ._set_status ("Delete done with errors")
                messagebox .showerror ("Delete","\n".join (errs ))
            else :
                self ._set_status ("Delete completed")
        threading .Thread (target =work ,daemon =True ).start ()

    def _rmdir_recursive (self ,path ):
        for e in self ._sftp .listdir_attr (path ):
            rp =os .path .join (path ,e .filename )
            if stat .S_ISDIR (e .st_mode ):
                self ._rmdir_recursive (rp )
            else :
                self ._sftp .remove (rp )
        self ._sftp .rmdir (path )

    def _on_mkdir (self ):
        name =self ._prompt ("New folder name:")
        if not name :
            return 
        def work ():
            if not self ._ensure_conn ():
                return 
            try :
                self ._sftp .mkdir (os .path .join (self .current_path .get ()or '/',name ))
                self ._set_status ("Folder created")
                self ._list_dir ()
            except Exception as e :
                self ._set_status (f"Mkdir failed: {e}")
        threading .Thread (target =work ,daemon =True ).start ()

    def _on_rename (self ):
        item =self .tree .focus ()
        if not item :
            return 
        old =self .tree .item (item ,'text')or ''
        new =self ._prompt (f"Rename '{old}' to:",initial =old )
        if not new or new ==old :
            return 
        def work ():
            if not self ._ensure_conn ():
                return 
            base =self .current_path .get ()or '/'
            try :
                self ._sftp .rename (os .path .join (base ,old ),os .path .join (base ,new ))
                self ._set_status ("Renamed")
                self ._list_dir ()
            except Exception as e :
                self ._set_status (f"Rename failed: {e}")
        threading .Thread (target =work ,daemon =True ).start ()

        # transfers
    def _transfer_many (self ,files ,remote_dir ,upload =True ):
        def work ():
            if upload :
                total =len (files )
                done =0 
                for f in files :
                    self ._upload_one (f ,os .path .join (remote_dir ,os .path .basename (f )))
                    done +=1 
                    self ._progress (done ,total )
                self ._set_status ("Upload completed")
                self ._list_dir ()
        threading .Thread (target =work ,daemon =True ).start ()

    def _download_many (self ,items ):
        def work ():
            total =len (items )
            done =0 
            for remote_path ,local_path in items :
                self ._download_one (remote_path ,local_path )
                done +=1 
                self ._progress (done ,total )
            self ._set_status ("Download completed")
        threading .Thread (target =work ,daemon =True ).start ()

    def _progress (self ,done ,total ):
        pct =(done /max (total ,1 ))*100.0 
        self .after (0 ,lambda :self .progress_var .set (pct ))

    def _upload_one (self ,local_path ,remote_path ):
    # try scpexe if requested
        if self .use_scp .get ()and self .scp_path .get ()and os .path .isfile (self .scp_path .get ()):
            try :
                self ._run_scp (local_path ,f"{self.ip_var.get()}:{remote_path}")
                return True 
            except Exception as e :
                self ._set_status (f"scp upload failed, fallback to SFTP: {e}")
                # fallback to sftp
        if not self ._ensure_conn ():
            return False 
        try :
            self ._sftp_put_with_progress (local_path ,remote_path )
            return True 
        except Exception as e :
            self ._set_status (f"Upload failed: {e}")
            return False 

    def _download_one (self ,remote_path ,local_path ):
    # scpexe path form: user@ip:remote -> local
        if self .use_scp .get ()and self .scp_path .get ()and os .path .isfile (self .scp_path .get ()):
            try :
                self ._run_scp (f"{self.ip_var.get()}:{remote_path}",local_path )
                return True 
            except Exception as e :
                self ._set_status (f"scp download failed, fallback to SFTP: {e}")
        if not self ._ensure_conn ():
            return False 
        try :
            self ._sftp_get_with_progress (remote_path ,local_path )
            return True 
        except Exception as e :
            self ._set_status (f"Download failed: {e}")
            return False 

    def _run_scp (self ,src ,dst ):
    # uses the systems scp assumes key-based auth is configured on the device
        ip =self .ip_var .get ().strip ()
        if not ip :
            raise RuntimeError ("No target IP")
        scp =self .scp_path .get ()
        # attempt to pass port if we can query it from an existing connection
        port =22 
        try :
            if self ._client :
                t =self ._client .get_transport ()
                if t :
                    port =t .getpeername ()[1 ]
        except Exception :
            pass 
        args =[scp ,"-P",str (port ),src ,dst ]
        self ._set_status ("scp running...")
        res =subprocess .run (args ,capture_output =True ,text =True )
        if res .returncode !=0 :
            raise RuntimeError (res .stderr .strip ()or res .stdout .strip ()or f"scp failed {res.returncode}")

    def _sftp_put_with_progress (self ,local_path ,remote_path ):
        def cb (x ,y ):
            pct =(x /max (y ,1 ))*100.0 
            self .after (0 ,lambda :self .progress_var .set (pct ))
        self ._set_status (f"Uploading {os.path.basename(local_path)}...")
        self ._sftp .put (local_path ,remote_path ,callback =cb )

    def _sftp_get_with_progress (self ,remote_path ,local_path ):
        def cb (x ,y ):
            pct =(x /max (y ,1 ))*100.0 
            self .after (0 ,lambda :self .progress_var .set (pct ))
        self ._set_status (f"Downloading {os.path.basename(remote_path)}...")
        self ._sftp .get (remote_path ,local_path ,callback =cb )

        # small prompt
    def _prompt (self ,title ,initial =""):
        top =tk .Toplevel (self )
        top .title (title )
        top .transient (self .winfo_toplevel ())
        v =tk .StringVar (value =initial )
        ttk .Label (top ,text =title ).pack (padx =10 ,pady =8 )
        e =ttk .Entry (top ,textvariable =v ,width =40 )
        e .pack (padx =10 ,pady =6 )
        e .focus_set ()
        btns =ttk .Frame (top )
        btns .pack (pady =8 )
        out ={"ok":False }
        def ok ():
            out ["ok"]=True 
            top .destroy ()
        def cancel ():
            top .destroy ()
        ttk .Button (btns ,text ="OK",command =ok ).pack (side =tk .LEFT ,padx =6 )
        ttk .Button (btns ,text ="Cancel",command =cancel ).pack (side =tk .LEFT ,padx =6 )
        top .grab_set ()
        self .wait_window (top )
        return v .get ()if out ["ok"]else None 
