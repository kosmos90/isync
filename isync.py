import os 
import threading 
import tkinter as tk 
from tkinter import filedialog ,messagebox ,simpledialog 
from tkinter import ttk 
from tkinter .scrolledtext import ScrolledText 
import tempfile 
import time 
import zipfile 
import shutil 
import urllib .request 
import json 
import plistlib 

# third-party
try :
    import paramiko 
except ImportError :
    paramiko =None 
try :
    from PIL import Image # type: ignore
except Exception :
    Image =None 
try :
    from tkinterdnd2 import DND_FILES ,TkinterDnD # type: ignore
    _DND_AVAILABLE =True 
except Exception :
    DND_FILES =None 
    TkinterDnD =None 
    _DND_AVAILABLE =False 

    # local
ExplorerFrame =None 
try :
# prefer new module name
    from ixplorer_frame import ExplorerFrame # type: ignore
except Exception :
    try :
        from isyncexplorer import ExplorerFrame # type: ignore
    except Exception :
        ExplorerFrame =None 


class IPAGui ((TkinterDnD .Tk if _DND_AVAILABLE else tk .Tk )):
    def __init__ (self ):
        super ().__init__ ()
        self .title ("iPhone IPA Installer")
        # size to comfortably fit all controls without scrolling
        self .geometry ("900x720")
        self .resizable (True ,True )
        # professional look and sane minimums
        try :
            self .minsize (920 ,700 )
            style =ttk .Style ()
            if 'vista' in style .theme_names ():
                style .theme_use ('vista')
            elif 'clam' in style .theme_names ():
                style .theme_use ('clam')
        except Exception :
            pass 

        self .ipa_path =tk .StringVar ()
        self .iphone_ip =tk .StringVar ()
        self .iphone_port =tk .IntVar (value =22 )
        self .username =tk .StringVar (value ="root")
        self .password =tk .StringVar ()
        # histories for dropdowns
        self ._ip_history =["192.168.178.67"]
        self ._user_history =["root"]
        self ._key_history =[]
        self ._ipa_history =[]
        self ._appdir_history =[]
        self .app_dir_path =tk .StringVar ()

        # auth type: rsa dss both
        self .auth_choice =tk .StringVar (value ="Both")
        # use password too default true globally
        self .use_password =tk .BooleanVar (value =True )
        self .private_key_path =tk .StringVar ()
        # raw output mode for ipainstaller no extra messages
        self .raw_output =tk .BooleanVar (value =True )
        # commands-only mode: only show the commands we run no outputs
        self .commands_only =tk .BooleanVar (value =True )

        # preferences
        self .no_respring =tk .BooleanVar (value =False )

        # installer choice: ipainstaller or appinst appinst not implemented yet
        self .installer_choice =tk .StringVar (value ="ipainstaller")

        # ipainstaller flags
        self .flags ={
        '-a':tk .BooleanVar (value =False ),
        '-b':tk .BooleanVar (value =False ),
        '-B':tk .BooleanVar (value =False ),
        '-c':tk .BooleanVar (value =False ),
        '-d':tk .BooleanVar (value =False ),
        '-f':tk .BooleanVar (value =False ),
        '-h':tk .BooleanVar (value =False ),
        '-i':tk .BooleanVar (value =False ),
        '-l':tk .BooleanVar (value =False ),
        '-n':tk .BooleanVar (value =False ),
        '-o':tk .BooleanVar (value =False ),
        '-q':tk .BooleanVar (value =False ),
        '-Q':tk .BooleanVar (value =False ),
        '-r':tk .BooleanVar (value =False ),
        '-u':tk .BooleanVar (value =False ),
        }
        # args for flags that need them
        self .flag_args ={
        '-b':tk .StringVar (),# app_id
        '-B':tk .StringVar (),# app_id
        '-i':tk .StringVar (),# app_ids
        '-o':tk .StringVar (),# output_path
        '-u':tk .StringVar (),# app_ids
        }

        # command previews
        self .command_preview =tk .StringVar (value ="")
        self .jf_command_preview =tk .StringVar (value ="")

        # presets and profiles
        self .preset_name =tk .StringVar (value ="")
        self .profiles ={} # name -> dict of connection fields
        self .profile_name =tk .StringVar (value ="")
        self .last_preset =tk .StringVar (value ="")

        # status bar
        self .status_text =tk .StringVar (value ="Ready")
        self .status_device =tk .StringVar (value ="")
        # status led internals
        self ._led_canvas =None 
        self ._led_item =None 
        self ._led_anim_job =None 
        self ._led_on =False 

        self ._build_ui ()
        # try to load settings after ui created to populate combos
        try :
            self ._load_settings ()
        except Exception :
            pass 
        # save settings on close
        self .protocol ("WM_DELETE_WINDOW",self ._on_close )
        # ensure geometry/layout is realized on first show
        try :
            self .update_idletasks ()
        except Exception :
            pass 

        # init command preview traces and compute initial preview
        try :
            self ._init_validation_styles ()
            self ._init_command_preview_traces ()
            self ._update_command_preview ()
            self ._init_command_preview_traces ()
            self ._update_command_preview ()
            self ._init_jf_command_preview_traces ()
            self ._update_jf_command_preview ()
        except Exception :
            pass 

        # initialize icons static + animated
        try :
            self ._init_icon_system ()
        except Exception :
        # dont crash ui if icon init fails
            pass 

            # -----------------------------
            # icon system static + animated
            # -----------------------------

        # keyboard shortcuts
        try :
            self ._init_shortcuts ()
        except Exception :
            pass 

    def _asset_base (self ):
        try :
            return os .path .dirname (os .path .abspath (__file__ ))
        except Exception :
            return os .getcwd ()

    # -----------------------------
    # settings persistence + close
    # -----------------------------
    def _settings_path (self ):
        try :
            base =self ._asset_base ()
            return os .path .join (base ,"settings.json")
        except Exception :
            return "settings.json"

    def _save_settings (self ):
        try :
            data ={
            "connection":{
            "iphone_ip":self .iphone_ip .get (),
            "iphone_port":int (self .iphone_port .get ()or 22 ),
            "username":self .username .get (),
            "use_password":bool (self .use_password .get ()),
            "private_key_path":self .private_key_path .get (),
            # do not save plaintext password by default
            },
            "ui":{
            "installer_choice":self .installer_choice .get (),
            "raw_output":bool (self .raw_output .get ()),
            "commands_only":bool (self .commands_only .get ()),
            "no_respring":bool (self .no_respring .get ()),
            "geometry":self .geometry (),
            },
            "flags":{k :bool (v .get ())for k ,v in self .flags .items ()},
            "flag_args":{k :v .get ()for k ,v in self .flag_args .items ()},
            "histories":{
            "ip":self ._ip_history ,
            "user":self ._user_history ,
            "key":self ._key_history ,
            "ipa":self ._ipa_history ,
            "appdir":self ._appdir_history ,
            },
            "profiles":self .profiles ,
            "last_preset":self .last_preset .get (),
            "selected_profile":self .profile_name .get (),
            }
            with open (self ._settings_path (),'w',encoding ='utf-8')as f :
                json .dump (data ,f ,ensure_ascii =False ,indent =2 )
        except Exception :
            # non-fatal
            pass 

    def _load_settings (self ):
        try :
            sp =self ._settings_path ()
            if not os .path .exists (sp ):
                return 
            with open (sp ,'r',encoding ='utf-8')as f :
                data =json .load (f )
            c =data .get ("connection",{})
            self .iphone_ip .set (c .get ("iphone_ip",self .iphone_ip .get ()))
            self .iphone_port .set (int (c .get ("iphone_port",self .iphone_port .get ()or 22 )))
            self .username .set (c .get ("username",self .username .get ()))
            self .use_password .set (bool (c .get ("use_password",self .use_password .get ())))
            self .private_key_path .set (c .get ("private_key_path",self .private_key_path .get ()))

            ui =data .get ("ui",{})
            self .installer_choice .set (ui .get ("installer_choice",self .installer_choice .get ()))
            self .raw_output .set (bool (ui .get ("raw_output",self .raw_output .get ())))
            self .commands_only .set (bool (ui .get ("commands_only",self .commands_only .get ())))
            self .no_respring .set (bool (ui .get ("no_respring",self .no_respring .get ())))
            try :
                geom =ui .get ("geometry")
                if geom :
                    self .geometry (geom )
            except Exception :
                pass 

            fl =data .get ("flags",{})
            for k ,v in fl .items ():
                if k in self .flags :
                    try :
                        self .flags [k ].set (bool (v ))
                    except Exception :
                        pass 
            fla =data .get ("flag_args",{})
            for k ,v in fla .items ():
                if k in self .flag_args :
                    try :
                        self .flag_args [k ].set (str (v ))
                    except Exception :
                        pass 

            his =data .get ("histories",{})
            self ._ip_history =list (his .get ("ip",self ._ip_history ))
            self ._user_history =list (his .get ("user",self ._user_history ))
            self ._key_history =list (his .get ("key",self ._key_history ))
            self ._ipa_history =list (his .get ("ipa",self ._ipa_history ))
            self ._appdir_history =list (his .get ("appdir",self ._appdir_history ))

            # profiles/presets
            self .profiles =dict (data .get ("profiles",{}))
            self .last_preset .set (data .get ("last_preset",self .last_preset .get ()))
            self .profile_name .set (data .get ("selected_profile",self .profile_name .get ()))

            # refresh combos with new histories
            try :
                self ._refresh_combos ()
            except Exception :
                pass 
        except Exception :
            # non-fatal
            pass 

    def _on_close (self ):
        try :
            self ._save_settings ()
        except Exception :
            pass 
        try :
            # stop animation and cleanup temp icon dir
            try :
                self ._stop_icon_animation ()
            except Exception :
                pass 
            tmp =getattr (self ,"_icon_tempdir",None )
            if tmp and os .path .exists (tmp ):
                try :
                    shutil .rmtree (tmp ,ignore_errors =True )
                except Exception :
                    pass 
        finally :
            try :
                self .destroy ()
            except Exception :
                pass 

    # -----------------------------
    # command preview + test ssh
    # -----------------------------
    def _init_command_preview_traces (self ):
        # attach traces to update command preview when inputs change
        def attach (var ):
            try :
                var .trace_add ("write",lambda *a :self ._update_command_preview ())
            except Exception :
                pass 
        attach (self .ipa_path )
        attach (self .iphone_ip )
        attach (self .iphone_port )
        attach (self .username )
        attach (self .password )
        attach (self .use_password )
        attach (self .private_key_path )
        attach (self .installer_choice )
        for v in self .flags .values ():
            attach (v )
        for v in self .flag_args .values ():
            attach (v )

    def _update_command_preview (self ):
        try :
            # try to leverage existing arg collection if available
            try :
                args =self ._collect_ipainstaller_args ()
                if isinstance (args ,list ):
                    cmd =" ".join (self ._shell_quote (a )for a in args )
                else :
                    cmd =str (args )
            except Exception :
                # fallback minimal reconstruction
                parts =[self .installer_choice .get ()or "ipainstaller"]
                for k ,v in self .flags .items ():
                    if v .get ():
                        parts .append (k )
                for k ,v in self .flag_args .items ():
                    val =v .get ().strip ()
                    if val :
                        parts .extend ([k ,val ])
                ipa =self .ipa_path .get ().strip ()
                if ipa :
                    parts .append (ipa )
                cmd =" ".join (self ._shell_quote (p )for p in parts )
            self .command_preview .set (cmd )
        except Exception :
            # never crash ui
            pass 

    def _init_jf_command_preview_traces (self ):
        # attach traces to update jf command preview when inputs change
        def attach (var ):
            try :
                var .trace_add ("write",lambda *a :self ._update_jf_command_preview ())
            except Exception :
                pass 
        attach (self .ipa_path )
        try :
            attach (self .app_dir_path )
        except Exception :
            pass 
        attach (self .iphone_ip )
        attach (self .iphone_port )
        attach (self .username )
        attach (self .use_password )
        attach (self .private_key_path )

    def _update_jf_command_preview (self ):
        # build a simple jailfr3e command preview
        try :
            ipa = (self .ipa_path .get ()or "").strip ()
            appdir = (getattr (self ,'app_dir_path',tk .StringVar (value ="")).get ()or "").strip ()
            if ipa :
                cmd =f"jailfr3e install {self._shell_quote(ipa)}"
            elif appdir :
                cmd =f"jailfr3e appdrop {self._shell_quote(appdir)}"
            else :
                cmd ="jailfr3e"
            self .jf_command_preview .set (cmd )
        except Exception :
            pass 

    def _on_test_ssh (self ):
        def run ():
            try :
                client =self ._connect ()
                try :
                    if not self .commands_only .get ():
                        self ._log ("SSH test: Connected successfully.")
                    messagebox .showinfo ("SSH","Connected successfully.")
                finally :
                    try :
                        client .close ()
                    except Exception :
                        pass 
            except Exception as e :
                if not self .commands_only .get ():
                    self ._log (f"SSH test failed: {e}")
                messagebox .showerror ("SSH Test Failed",str (e ))
        try :
            self ._run_with_icon_anim (run )
        except Exception :
            # fallback without animation
            run ()

    # -----------------------------
    # validation + status bar
    # -----------------------------
    def _is_valid_ip (self ,ip :str ):
        try :
            parts =ip .split ('.')
            if len (parts )!=4 :
                return False 
            for p in parts :
                if not p .isdigit ():
                    return False 
                v =int (p )
                if v <0 or v >255 :
                    return False 
            return True 
        except Exception :
            return False 

    def _validate_ui (self ):
        # returns (ok, message)
        ip =self .iphone_ip .get ().strip ()
        ipa =self .ipa_path .get ().strip ()
        use_pw =bool (self .use_password .get ())
        key =self .private_key_path .get ().strip ()
        try :
            port =int (self .iphone_port .get ()or 0 )
        except Exception :
            port =0 
        if not ip or not self ._is_valid_ip (ip ):
            return False ,"enter a valid ip address"
        if port <=0 or port >65535 :
            return False ,"enter a valid port"
        if not ipa :
            return False ,"choose an ipa file"
        if not use_pw and not key :
            return False ,"provide a private key or enable password"
        if key and not os .path .exists (key ):
            return False ,"private key path not found"
        return True ,"ready"

    def _apply_validation (self ):
        # clear any previous styles
        try :
            self ._clear_invalids ()
        except Exception :
            pass 

        # granular checks for targeted highlighting
        ip =self .iphone_ip .get ().strip ()
        ipa =self .ipa_path .get ().strip ()
        use_pw =bool (self .use_password .get ())
        key =self .private_key_path .get ().strip ()
        try :
            port =int (self .iphone_port .get ()or 0 )
        except Exception :
            port =0 

        ok =True 
        msg ="ready"
        if not ip or not self ._is_valid_ip (ip ):
            ok =False 
            msg ="enter a valid ip address"
            self ._mark_invalid (getattr (self ,'ip_combo',None ),'combo',msg )
        elif port <=0 or port >65535 :
            ok =False 
            msg ="enter a valid port"
            self ._mark_invalid (getattr (self ,'port_entry',None ),'entry',msg )
        elif not ipa :
            ok =False 
            msg ="choose an ipa file"
            self ._mark_invalid (getattr (self ,'ipa_combo',None ),'combo',msg )
        elif (not use_pw )and (not key ):
            ok =False 
            msg ="provide a private key or enable password"
            self ._mark_invalid (getattr (self ,'key_combo',None ),'combo',msg )
        elif key and not os .path .exists (key ):
            ok =False 
            msg ="private key path not found"
            self ._mark_invalid (getattr (self ,'key_combo',None ),'combo',msg )

        # apply enabled state to buttons
        for btn in [getattr (self ,'install_btn',None ),getattr (self ,'run_ipainstaller_btn',None ),getattr (self ,'jf_install_btn',None )]:
            try :
                if btn is not None :
                    btn .configure (state =(tk .NORMAL if ok else tk .DISABLED ))
            except Exception :
                pass 
        self ._set_status (msg )

    def _init_validation_traces (self ):
        def attach (var ):
            try :
                var .trace_add ("write",lambda *a :self ._apply_validation ())
            except Exception :
                pass 
        attach (self .iphone_ip )
        attach (self .iphone_port )
        attach (self .ipa_path )
        attach (self .use_password )
        attach (self .private_key_path )

    def _set_status (self ,text :str ):
        try :
            self .status_text .set (text )
            self .status_device .set (f"{self.iphone_ip.get()}:{self.iphone_port.get()}")
        except Exception :
            pass 

    def _init_shortcuts (self ):
        try :
            # file open
            self .bind ("<Control-o>",lambda e :self ._choose_ipa ())
            self .bind ("<Control-O>",lambda e :self ._choose_ipa ())
            # install
            self .bind ("<Control-i>",lambda e :self ._on_install_click ())
            self .bind ("<Control-I>",lambda e :self ._on_install_click ())
            # clear output
            self .bind ("<Control-l>",lambda e :self ._clear_output ())
            self .bind ("<Control-L>",lambda e :self ._clear_output ())
            # respring
            self .bind ("<F5>",lambda e :self ._on_respring ())
        except Exception :
            pass 

    def _enter_busy (self ,msg ="Working…"):
        try :
            self ._set_status (msg )
            # visual busy cursor
            self .configure (cursor ="watch")
            # disable primary action buttons while running
            for btn in [getattr (self ,'install_btn',None ),getattr (self ,'run_ipainstaller_btn',None ),getattr (self ,'jf_install_btn',None )]:
                try :
                    if btn is not None :
                        btn .configure (state =tk .DISABLED )
                except Exception :
                    pass 
            # start status led pulse
            try :
                self ._start_led_anim ()
            except Exception :
                pass 
        except Exception :
            pass 

    def _leave_busy (self ):
        try :
            self .configure (cursor ="")
            # re-apply validation to restore correct enabled state
            self ._apply_validation ()
            self ._set_status ("Ready")
            try :
                self ._stop_led_anim ()
            except Exception :
                pass 
        except Exception :
            pass 

    def _init_icon_system (self ):
    # state
        self ._icon_fps =30 
        self ._icon_anim_job =None 
        self ._icon_anim_running =False 
        self ._icon_frame_index =0 
        self ._icon_frames =[]# list[tkphotoimage]
        self ._icon_tempdir =tempfile .mkdtemp (prefix ="isync_icon_")

        # paths
        self ._icon_static_path =os .path .join (self ._asset_base (),"imgtitle.png")
        self ._icon_gif_path =os .path .join (self ._asset_base (),"process_img.gif")

        # load static icon
        self ._set_static_icon ()
        # prepare animation frames
        self ._prepare_animation_frames ()

    def _set_static_icon (self ):
        try :
            if os .path .isfile (self ._icon_static_path ):
                self ._icon_static_img =tk .PhotoImage (file =self ._icon_static_path )
                self .iconphoto (True ,self ._icon_static_img )
        except Exception :
            pass 

    def _prepare_animation_frames (self ):
    # clear any existing
        self ._icon_frames =[]
        self ._icon_frame_index =0 

        if not os .path .isfile (self ._icon_gif_path ):
            return 

        try :
            if Image is not None :
            # extract frames to png files in temp then load as photoimage
                with Image .open (self ._icon_gif_path )as im :
                    frame_idx =0 
                    while True :
                        im .seek (frame_idx )
                        frame =im .convert ("RGBA")
                        out_path =os .path .join (self ._icon_tempdir ,f"frame_{frame_idx:03d}.png")
                        frame .save (out_path ,format ="PNG")
                        try :
                            self ._icon_frames .append (tk .PhotoImage (file =out_path ))
                        except Exception :
                            break 
                        frame_idx +=1 
            else :
            # fallback without pillow: load gif frames directly no png extraction
                idx =0 
                while True :
                    try :
                        frm =tk .PhotoImage (file =self ._icon_gif_path ,format =f"gif -index {idx}")
                        self ._icon_frames .append (frm )
                        idx +=1 
                    except Exception :
                        break 
        except Exception :
        # ignore errors keep static icon only
            self ._icon_frames =[]

    def _animate_tick (self ):
        if not self ._icon_anim_running or not self ._icon_frames :
            return 
        try :
            img =self ._icon_frames [self ._icon_frame_index %len (self ._icon_frames )]
            self .iconphoto (True ,img )
            self ._icon_frame_index =(self ._icon_frame_index +1 )%len (self ._icon_frames )
        except Exception :
        # stop animation on error
            self ._icon_anim_running =False 
            self ._set_static_icon ()
            return 
            # schedule next frame
        delay =int (1000 /max (1 ,self ._icon_fps ))
        self ._icon_anim_job =self .after (delay ,self ._animate_tick )

    def _start_icon_animation (self ):
        if self ._icon_anim_running :
            return 
        if not self ._icon_frames :
            return 
        self ._icon_anim_running =True 
        self ._icon_frame_index =0 
        # start on ui thread
        self .after (0 ,self ._animate_tick )

    def _stop_icon_animation (self ):
        self ._icon_anim_running =False 
        try :
            if self ._icon_anim_job is not None :
                try :
                    self .after_cancel (self ._icon_anim_job )
                except Exception :
                    pass 
                self ._icon_anim_job =None 
        finally :
        # restore static icon
            self ._set_static_icon ()

    def _run_with_icon_anim (self ,target ):
    # run target in background while animating icon at ~30 fps
        def runner ():
            try :
            # start on ui thread
                self .after (0 ,self ._start_icon_animation )
                self .after (0 ,lambda :self ._enter_busy ("Working…"))
                target ()
            finally :
            # stop on ui thread
                self .after (0 ,self ._leave_busy )
                self .after (0 ,self ._stop_icon_animation )
        threading .Thread (target =runner ,daemon =True ).start ()

    def _add_history (self ,hist_list ,value ,maxlen =15 ):
        v =(value or '').strip ()
        if not v :
            return 
            # deduplicate keep most recent at front
        if v in hist_list :
            hist_list .remove (v )
        hist_list .insert (0 ,v )
        # trim
        del hist_list [maxlen :]
        self ._refresh_combos ()

    def _refresh_combos (self ):
    # safely update all combobox values if they exist
        try :
            if hasattr (self ,'ipa_combo')and self .ipa_combo :
                self .ipa_combo ['values']=self ._ipa_history 
            if hasattr (self ,'jf_ipa_combo')and self .jf_ipa_combo :
                self .jf_ipa_combo ['values']=self ._ipa_history 
        except Exception :
            pass 
        try :
            if hasattr (self ,'user_combo')and self .user_combo :
                self .user_combo ['values']=self ._user_history 
            if hasattr (self ,'jf_user_combo')and self .jf_user_combo :
                self .jf_user_combo ['values']=self ._user_history 
        except Exception :
            pass 
        try :
            if hasattr (self ,'key_combo')and self .key_combo :
                self .key_combo ['values']=self ._key_history 
            if hasattr (self ,'jf_key_combo')and self .jf_key_combo :
                self .jf_key_combo ['values']=self ._key_history 
        except Exception :
            pass 
        try :
            if hasattr (self ,'ip_combo')and self .ip_combo :
                self .ip_combo ['values']=self ._ip_history 
            if hasattr (self ,'jf_ip_combo')and self .jf_ip_combo :
                self .jf_ip_combo ['values']=self ._ip_history 
        except Exception :
            pass 
        try :
            if hasattr (self ,'jf_app_combo')and self .jf_app_combo :
                self .jf_app_combo ['values']=self ._appdir_history 
        except Exception :
            pass 

    def _build_ui (self ):
    # notebook tabs
        notebook =ttk .Notebook (self )
        notebook .pack (fill =tk .BOTH ,expand =True )

        # installer tab
        inst_tab =ttk .Frame (notebook )
        notebook .add (inst_tab ,text ="Installer")

        # two-pane layout so output is always visible without scroll
        vpw =ttk .Panedwindow (inst_tab ,orient =tk .VERTICAL )
        vpw .pack (fill =tk .BOTH ,expand =True )
        top =ttk .Frame (vpw )
        bottom =ttk .Frame (vpw )
        # enforce minimum sizes so top never collapses to 0
        try :
            vpw .add (top ,minsize =320 )
            vpw .add (bottom ,minsize =140 )
        except Exception :
            vpw .add (top )
            vpw .add (bottom )
        # initial sizes (after layout realized)
        def _init_sash ():
            try :
                h =vpw .winfo_height ()
                if h <=1 :
                    self .after (50 ,_init_sash )
                    return 
                vpw .sashpos (0 ,int (h *0.45 ))
            except Exception :
                pass 
        self .after (0 ,_init_sash )
        # build main content in top pane
        main =top 
        if isinstance (main ,ttk .Frame ):
            try :
                main .configure (padding =10 )
            except Exception :
                pass 

        # source ipa selection
        src =ttk .LabelFrame (main ,text ="IPA selection")
        src .pack (fill =tk .X ,padx =5 ,pady =5 )
        self .ipa_combo =ttk .Combobox (src ,textvariable =self .ipa_path ,values =self ._ipa_history )
        self .ipa_combo .pack (side =tk .LEFT ,fill =tk .X ,expand =True ,padx =5 ,pady =5 )
        ttk .Button (src ,text ="Browse...",command =self ._choose_ipa ).pack (side =tk .LEFT ,padx =5 ,pady =5 )

        # connection settings
        conn =ttk .LabelFrame (main ,text ="Connection")
        conn .pack (fill =tk .X ,padx =5 ,pady =5 )
        row =ttk .Frame (conn )
        row .pack (fill =tk .X )
        ttk .Label (row ,text ="iPhone IP:").pack (side =tk .LEFT )
        self .ip_combo =ttk .Combobox (row ,width =18 ,textvariable =self .iphone_ip ,values =self ._ip_history )
        self .ip_combo .pack (side =tk .LEFT ,padx =5 )
        ttk .Label (row ,text ="Port:").pack (side =tk .LEFT )
        self .port_entry =ttk .Entry (row ,width =6 ,textvariable =self .iphone_port )
        self .port_entry .pack (side =tk .LEFT ,padx =5 )
        ttk .Label (row ,text ="User:").pack (side =tk .LEFT )
        self .user_combo =ttk .Combobox (row ,width =12 ,textvariable =self .username ,values =self ._user_history )
        self .user_combo .pack (side =tk .LEFT ,padx =5 )

        row2 =ttk .Frame (conn )
        row2 .pack (fill =tk .X ,pady =2 )
        ttk .Label (row2 ,text ="Private Key:").pack (side =tk .LEFT )
        self .key_combo =ttk .Combobox (row2 ,width =42 ,textvariable =self .private_key_path ,values =self ._key_history )
        self .key_combo .pack (side =tk .LEFT ,padx =5 )
        ttk .Button (row2 ,text ="Browse...",command =self ._choose_key ).pack (side =tk .LEFT )

        row3 =ttk .Frame (conn )
        row3 .pack (fill =tk .X ,pady =2 )
        ttk .Label (row3 ,text ="Auth Type:").pack (side =tk .LEFT )
        ttk .Combobox (row3 ,width =8 ,textvariable =self .auth_choice ,values =["RSA","DSS","Both"]).pack (side =tk .LEFT ,padx =5 )
        ttk .Label (row3 ,text ="Auth:").pack (side =tk .LEFT )
        ttk .Radiobutton (row3 ,text ="RSA",value ="RSA",variable =self .auth_choice ).pack (side =tk .LEFT )
        ttk .Radiobutton (row3 ,text ="DSS",value ="DSS",variable =self .auth_choice ).pack (side =tk .LEFT )
        ttk .Radiobutton (row3 ,text ="Both",value ="BOTH",variable =self .auth_choice ).pack (side =tk .LEFT )
        ttk .Checkbutton (row3 ,text ="Also use password",variable =self .use_password ).pack (side =tk .LEFT ,padx =10 )
        self .password_entry =ttk .Entry (row3 ,show ='*',width =18 ,textvariable =self .password )
        self .password_entry .pack (side =tk .LEFT )

        # test ssh button row
        row4 =ttk .Frame (conn )
        row4 .pack (fill =tk .X ,pady =2 )
        ttk .Button (row4 ,text ="Test SSH",command =self ._on_test_ssh ).pack (side =tk .LEFT ,padx =5 ,pady =2 )

        # profiles row
        prof =ttk .Frame (conn )
        prof .pack (fill =tk .X ,pady =2 )
        ttk .Label (prof ,text ="Profile:").pack (side =tk .LEFT )
        self .profile_combo =ttk .Combobox (prof ,width =20 ,textvariable =self .profile_name ,values =sorted (list (self .profiles .keys ())))
        self .profile_combo .pack (side =tk .LEFT ,padx =5 )
        ttk .Button (prof ,text ="Save",command =self ._profile_save ).pack (side =tk .LEFT ,padx =2 )
        ttk .Button (prof ,text ="Load",command =self ._profile_load ).pack (side =tk .LEFT ,padx =2 )
        ttk .Button (prof ,text ="Delete",command =self ._profile_delete ).pack (side =tk .LEFT ,padx =2 )

        # installer choice
        inst =ttk .LabelFrame (main ,text ="Installer")
        inst .pack (fill =tk .X ,padx =5 ,pady =5 )
        ttk .Radiobutton (inst ,text ="ipainstaller",value ="ipainstaller",variable =self .installer_choice ).pack (side =tk .LEFT ,padx =5 )
        ttk .Radiobutton (inst ,text ="appinst",value ="appinst",variable =self .installer_choice ).pack (side =tk .LEFT ,padx =5 )

        # ipainstaller options removed per request

                # actions
        actions =ttk .Frame (main )
        actions .pack (fill =tk .X ,pady =6 )
        self .install_btn =ttk .Button (actions ,text ="Install IPA",command =self ._on_install_click )
        self .install_btn .pack (side =tk .LEFT )
        self .run_ipainstaller_btn =ttk .Button (actions ,text ="Advanced: Run ipainstaller only",command =self ._on_run_ipainstaller_only )
        self .run_ipainstaller_btn .pack (side =tk .LEFT ,padx =6 )
        ttk .Checkbutton (actions ,text ="Raw ipainstaller output only",variable =self .raw_output ).pack (side =tk .LEFT ,padx =10 )
        ttk .Checkbutton (actions ,text ="Show only commands",variable =self .commands_only ).pack (side =tk .LEFT )

        # command preview
        preview =ttk .LabelFrame (main ,text ="Command Preview")
        preview .pack (fill =tk .X ,padx =5 ,pady =5 )
        self .command_entry =ttk .Entry (preview ,textvariable =self .command_preview ,state ="readonly" )
        self .command_entry .pack (side =tk .LEFT ,fill =tk .X ,expand =True ,padx =5 ,pady =5 )
        ttk .Button (preview ,text ="Copy",command =lambda : (self .clipboard_clear (),self .clipboard_append (self .command_preview .get ())) ).pack (side =tk .LEFT ,padx =5 )

        # status bar (bottom of Installer tab)
        # separator above status to delineate footer
        try :
            ttk .Separator (inst_tab ,orient =tk .HORIZONTAL ).pack (fill =tk .X ,side =tk .BOTTOM )
        except Exception :
            pass 
        status =ttk .Frame (inst_tab )
        status .pack (fill =tk .X ,side =tk .BOTTOM )
        # small led indicator on the left
        try :
            self ._led_canvas =tk .Canvas (status ,width =12 ,height =12 ,highlightthickness =0 ,bd =0 )
            self ._led_item =self ._led_canvas .create_oval (2 ,2 ,10 ,10 ,fill ="#9aa0a6" ,outline ="#777" )
            self ._led_canvas .pack (side =tk .LEFT ,padx =6 ,pady =2 )
        except Exception :
            pass 
        ttk .Label (status ,textvariable =self .status_text ).pack (side =tk .LEFT ,padx =6 ,pady =2 )
        ttk .Label (status ,textvariable =self .status_device ,foreground ="gray" ).pack (side =tk .RIGHT ,padx =6 ,pady =2 )

        # tooltips basic
        try :
            self ._add_tooltip (self .command_entry ,"exact command that will run on device")
            self ._add_tooltip (self .profile_combo ,"manage connection profiles")
            # removed preset combo
            self ._add_tooltip (self .ipa_combo ,"select or drop an ipa file")
            self ._add_tooltip (self .ip_combo ,"device ip address")
            self ._add_tooltip (self .user_combo ,"ssh username usually root")
            self ._add_tooltip (self .key_combo ,"path to private key on this pc")
            self ._add_tooltip (self .install_btn ,"install ipa with selected options")
            self ._add_tooltip (self .run_ipainstaller_btn ,"run ipainstaller only with flags")
        except Exception :
            pass 

        # tools
        tools =ttk .LabelFrame (main ,text ="Tools")
        tools .pack (fill =tk .X ,padx =5 ,pady =5 )
        ttk .Button (tools ,text ="Peek / (root)",command =self ._on_peek_root ).pack (side =tk .LEFT ,padx =4 ,pady =4 )
        ttk .Button (tools ,text ="Respring (killall SpringBoard)",command =self ._on_respring ).pack (side =tk .LEFT ,padx =4 ,pady =4 )
        ttk .Button (tools ,text ="Check AppSync status",command =self ._on_check_appsync ).pack (side =tk .LEFT ,padx =4 ,pady =4 )
        ttk .Button (tools ,text ="Install AppSync 116.0",command =self ._on_install_appsync ).pack (side =tk .LEFT ,padx =4 ,pady =4 )

        # output
        out =ttk .LabelFrame (bottom ,text ="Output")
        out .pack (fill =tk .BOTH ,expand =True ,padx =5 ,pady =5 )
        self .output =ScrolledText (out ,height =16 ,wrap =tk .WORD ,state =tk .DISABLED )
        # dark theme for output
        try :
            self .output .configure (background ="#0d1117" ,foreground ="#d1d5da" ,insertbackground ="#d1d5da" )
            self .output .tag_configure ('dir',foreground ="#4ea1ff")
            self .output .tag_configure ('app',foreground ="#00d2ff")
            self .output .tag_configure ('exec',foreground ="#2bd46b")
            self .output .tag_configure ('warn',foreground ="#ffd866")
            self .output .tag_configure ('error',foreground ="#ff6b6b")
            self .output .tag_configure ('path',foreground ="#c792ea")
        except Exception :
            pass 
        self .output .pack (fill =tk .BOTH ,expand =True )

        # ixplorer tab
        if ExplorerFrame is not None :
            try :
                explorer_tab =ExplorerFrame (
                notebook ,
                get_connection =self ._connect ,
                ip_var =self .iphone_ip ,
                )
                notebook .add (explorer_tab ,text ="iXplorer")
            except Exception as e :
            # fallback: show tab with error message
                err_tab =ttk .Frame (notebook )
                ttk .Label (err_tab ,text =f"iXplorer failed to load: {e}").pack (padx =10 ,pady =10 )
                notebook .add (err_tab ,text ="iXplorer")
        else :
        # if import failed still add a placeholder tab
            placeholder =ttk .Frame (notebook )
            ttk .Label (placeholder ,text ="iXplorer module not available.").pack (padx =10 ,pady =10 )
            notebook .add (placeholder ,text ="iXplorer")

            # applications tab lists /applications or /var/jb/applications with icons
        try :
            from applications_frame import ApplicationsFrame # local import to avoid hard dep if missing
            apps_tab =ApplicationsFrame (
            notebook ,
            get_connection =self ._connect ,
            )
            notebook .add (apps_tab ,text ="Applications")
        except Exception as e :
            apps_err =ttk .Frame (notebook )
            ttk .Label (apps_err ,text =f"Applications tab failed to load: {e}").pack (padx =10 ,pady =10 )
            notebook .add (apps_err ,text ="Applications")

            # jailfr3e-installipa tab
        jf_tab =ttk .Frame (notebook )
        notebook .add (jf_tab ,text ="JAILFR3E-INSTALLIPA")
        jf_main =ttk .Frame (jf_tab )
        jf_main .pack (fill =tk .BOTH ,expand =True ,padx =10 ,pady =10 )
        # connection/auth reuse same vars
        jf_conn =ttk .LabelFrame (jf_main ,text ="Connection & Auth (uses same settings)")
        jf_conn .pack (fill =tk .X ,padx =5 ,pady =5 )
        jf_row =ttk .Frame (jf_conn )
        jf_row .pack (fill =tk .X )
        ttk .Label (jf_row ,text ="iPhone IP:").pack (side =tk .LEFT )
        self .jf_ip_combo =ttk .Combobox (jf_row ,width =18 ,textvariable =self .iphone_ip ,values =self ._ip_history )
        self .jf_ip_combo .pack (side =tk .LEFT ,padx =5 )
        ttk .Label (jf_row ,text ="Port:").pack (side =tk .LEFT )
        ttk .Entry (jf_row ,width =6 ,textvariable =self .iphone_port ).pack (side =tk .LEFT ,padx =5 )
        ttk .Label (jf_row ,text ="User:").pack (side =tk .LEFT )
        self .jf_user_combo =ttk .Combobox (jf_row ,width =12 ,textvariable =self .username ,values =self ._user_history )
        self .jf_user_combo .pack (side =tk .LEFT ,padx =5 )
        ttk .Checkbutton (jf_row ,text ="Also use password",variable =self .use_password ).pack (side =tk .LEFT ,padx =10 )
        ttk .Entry (jf_row ,show ='*',width =18 ,textvariable =self .password ).pack (side =tk .LEFT )
        jf_row2 =ttk .Frame (jf_conn )
        jf_row2 .pack (fill =tk .X ,pady =2 )
        ttk .Label (jf_row2 ,text ="Private Key:").pack (side =tk .LEFT )
        self .jf_key_combo =ttk .Combobox (jf_row2 ,width =42 ,textvariable =self .private_key_path ,values =self ._key_history )
        self .jf_key_combo .pack (side =tk .LEFT ,padx =5 )
        ttk .Button (jf_row2 ,text ="Browse...",command =self ._choose_key ).pack (side =tk .LEFT )
        jf_row3 =ttk .Frame (jf_conn )
        jf_row3 .pack (fill =tk .X ,pady =2 )
        ttk .Label (jf_row3 ,text ="Auth Type:").pack (side =tk .LEFT )
        ttk .Combobox (jf_row3 ,width =8 ,textvariable =self .auth_choice ,values =["RSA","DSS","Both"]).pack (side =tk .LEFT ,padx =5 )
        jf_src =ttk .LabelFrame (jf_main ,text ="IPA selection")
        jf_src .pack (fill =tk .X ,padx =5 ,pady =5 )
        self .jf_ipa_combo =ttk .Combobox (jf_src ,textvariable =self .ipa_path ,values =self ._ipa_history )
        self .jf_ipa_combo .pack (side =tk .LEFT ,fill =tk .X ,expand =True ,padx =5 ,pady =5 )
        ttk .Button (jf_src ,text ="Browse...",command =self ._choose_ipa ).pack (side =tk .LEFT ,padx =5 ,pady =5 )
        jf_app =ttk .LabelFrame (jf_main ,text ="AppDrop: .app folder (optional if IPA provided)")
        jf_app .pack (fill =tk .X ,padx =5 ,pady =5 )
        self .jf_app_combo =ttk .Combobox (jf_app ,textvariable =self .app_dir_path ,values =self ._appdir_history )
        self .jf_app_combo .pack (side =tk .LEFT ,fill =tk .X ,expand =True ,padx =5 ,pady =5 )
        ttk .Button (jf_app ,text ="Browse...",command =self ._choose_app_dir ).pack (side =tk .LEFT ,padx =5 ,pady =5 )

        # jf command preview
        jf_prev =ttk .LabelFrame (jf_main ,text ="Command Preview")
        jf_prev .pack (fill =tk .X ,padx =5 ,pady =5 )
        self .jf_command_entry =ttk .Entry (jf_prev ,textvariable =self .jf_command_preview ,state ="readonly" )
        self .jf_command_entry .pack (side =tk .LEFT ,fill =tk .X ,expand =True ,padx =5 ,pady =5 )
        ttk .Button (jf_prev ,text ="Copy",command =lambda : (self .clipboard_clear (),self .clipboard_append (self .jf_command_preview .get ())) ).pack (side =tk .LEFT ,padx =5 ,pady =5 )

        # enable drag-and-drop on jailfr3e tab optional if tkinterdnd2 available
        try :
            if _DND_AVAILABLE :
            # register the jf_main container as a drop target
                jf_main .drop_target_register (DND_FILES )
                jf_main .dnd_bind ('<<Drop>>',self ._on_jf_drop )
        except Exception :
            pass 
        jf_info =ttk .LabelFrame (jf_main ,text ="About")
        jf_info .pack (fill =tk .X ,padx =5 ,pady =5 )
        ttk .Label (jf_info ,text ="Installs by extracting .app from IPA and copying to /var/mobile/Payload, then respring + uicache. For decrypted/unsigned apps.").pack (anchor =tk .W ,padx =6 ,pady =4 )
        jf_actions =ttk .Frame (jf_main )
        jf_actions .pack (fill =tk .X ,pady =6 )
        ttk .Button (jf_actions ,text ="Install via JAILFR3E",command =self ._on_jailfree_install ).pack (side =tk .LEFT )
        ttk .Button (jf_actions ,text ="Install via AppDrop (.app→zip)",command =self ._on_appdrop_install ).pack (side =tk .LEFT ,padx =8 )
        ttk .Button (jf_actions ,text ="Batch Install IPAs…",command =self ._on_batch_jf_ipas ).pack (side =tk .LEFT ,padx =8 )
        ttk .Button (jf_actions ,text ="Batch AppDrop Folders…",command =self ._on_batch_appdrop ).pack (side =tk .LEFT ,padx =8 )
        ttk .Checkbutton (jf_actions ,text ="Don't respring after install",variable =self .no_respring ).pack (side =tk .LEFT ,padx =8 )
        jf_extras =ttk .LabelFrame (jf_main ,text ="Extras")
        jf_extras .pack (fill =tk .X ,padx =5 ,pady =5 )
        ttk .Button (jf_extras ,text ="Clean leftovers (zip/app)",command =self ._on_clean_leftovers ).pack (side =tk .LEFT ,padx =5 ,pady =5 )
        ttk .Button (jf_extras ,text ="uicache (as mobile)",command =self ._on_uicache_mobile ).pack (side =tk .LEFT ,padx =5 ,pady =5 )
        ttk .Button (jf_extras ,text ="Install .deb…",command =self ._on_install_deb ).pack (side =tk .LEFT ,padx =5 ,pady =5 )
        ttk .Button (jf_extras ,text ="Install .deb from URL…",command =self ._on_install_deb_url ).pack (side =tk .LEFT ,padx =5 ,pady =5 )
        ttk .Button (jf_extras ,text ="Uninstall package…",command =self ._on_uninstall_deb ).pack (side =tk .LEFT ,padx =5 ,pady =5 )
        ttk .Button (jf_extras ,text ="Save Output…",command =self ._on_save_jf_output ).pack (side =tk .LEFT ,padx =5 ,pady =5 )
        jf_out =ttk .LabelFrame (jf_main ,text ="Output")
        jf_out .pack (fill =tk .BOTH ,expand =True ,padx =5 ,pady =5 )
        self .jf_output =ScrolledText (jf_out ,height =12 ,wrap =tk .WORD ,state =tk .DISABLED )
        try :
            self .jf_output .configure (background ="#0d1117" ,foreground ="#d1d5da" ,insertbackground ="#d1d5da" )
            self .jf_output .tag_configure ('dir',foreground ="#4ea1ff")
            self .jf_output .tag_configure ('app',foreground ="#00d2ff")
            self .jf_output .tag_configure ('exec',foreground ="#2bd46b")
            self .jf_output .tag_configure ('warn',foreground ="#ffd866")
            self .jf_output .tag_configure ('error',foreground ="#ff6b6b")
            self .jf_output .tag_configure ('path',foreground ="#c792ea")
        except Exception :
            pass 
        self .jf_output .pack (fill =tk .BOTH ,expand =True )

        # about tab licenses and credits
        about_tab =ttk .Frame (notebook )
        notebook .add (about_tab ,text ="About")
        about_box =ScrolledText (about_tab ,height =20 ,wrap =tk .WORD )
        about_box .pack (fill =tk .BOTH ,expand =True ,padx =10 ,pady =10 )
        about_text =(
        "iSync — iPhone IPA Installer & Explorer\n\n"
        "This is a preliminary PySide6 port using the Fusion style.\n"
        "Functional parity with the Tk app (isync.py) will be added incrementally.\n"
        "Made by Filip (https://github.com/kosmos90) (iFilip :>)\n\n"
        "Credits and Licenses:\n\n"
        "- Python & Tkinter: Python Software Foundation License.\n"
        "  https://www.python.org/psf/license/\n\n"
        "- Paramiko (SSH/SFTP): LGPL 2.1+ (see project for details).\n"
        "  https://www.paramiko.org/\n\n"
        "- Pillow (PIL): HPND / PIL License.\n"
        "  https://python-pillow.org/\n\n"
        "- pillow-avif-plugin (if installed): MIT License.\n"
        "  https://github.com/Knio/pillow-avif-plugin\n\n"
        "- OpenSSH tools (scp.exe/ssh.exe): BSD-style License.\n"
        "  https://www.openssh.com/portable.html\n\n"
        "- Info-ZIP unzip (device): Info-ZIP License.\n"
        "  http://infozip.sourceforge.net/\n\n"
        "- appinst (if used on device): subject to its respective upstream license.\n\n"
        "Assets:\n\n"
        "- Default app icon (defapp.avif/defapp.png): from Freepik, used under their Terms of Use.\n"
        "  https://www.freepik.com/legal/terms-of-use\n\n"
        "Notes:\n"
        "- This application may invoke third-party utilities present on your system or device.\n"
        "- All trademarks and product names are the property of their respective owners.\n"
        )
        about_box .insert (tk .END ,about_text )
        about_box .configure (state =tk .DISABLED )

        if not self .commands_only .get ():
            self ._log ("Ready. Select an IPA, enter device IP, choose auth, and click Install.")

        # keyboard shortcuts
        try :
            self .bind ("<Control-o>",lambda e :self ._choose_ipa ())
            self .bind ("<Control-i>",lambda e :self ._on_install_click ())
            self .bind ("<Control-l>",lambda e :self ._clear_output ())
            self .bind ("<F5>",lambda e :self ._on_respring ())
        except Exception :
            pass 

            # ui helpers
    def _choose_ipa (self ):
        path =filedialog .askopenfilename (title ="Select IPA",filetypes =[("IPA Files","*.ipa"),("All Files","*.*")])
        if path :
            self .ipa_path .set (path )
            self ._add_history (self ._ipa_history ,path )
            self ._refresh_combos ()

    def _choose_key (self ):
        path =filedialog .askopenfilename (title ="Select Private Key",filetypes =[("Key Files","*.pem *.ppk *.key *.*"),("All Files","*.*")])
        if path :
            self .private_key_path .set (path )
            self ._add_history (self ._key_history ,path )
            self ._refresh_combos ()

    # -----------------------------
    # presets and profiles helpers
    # -----------------------------
    def _apply_preset (self ,name :str ):
        presets ={
        "Clean install":{
        "flags":{'-f':True ,'-r':False ,'-q':False ,'-Q':False ,'-n':False },
        "args":{}
        },
        "Reinstall":{
        "flags":{'-r':True ,'-f':False },
        "args":{}
        },
        "Force + Quiet":{
        "flags":{'-f':True ,'-q':True ,'-Q':True },
        "args":{}
        },
        "No respring":{
        "flags":{'-n':True },
        "args":{}
        },
        "Minimal output":{
        "flags":{'-q':True ,'-Q':True },
        "args":{}
        },
        }
        p =presets .get (name )
        if not p :
            return 
        for k ,v in p ["flags"].items ():
            if k in self .flags :
                try :
                    self .flags [k ].set (bool (v ))
                except Exception :
                    pass 
        for k ,v in p ["args"].items ():
            if k in self .flag_args :
                try :
                    self .flag_args [k ].set (str (v ))
                except Exception :
                    pass 
        self .last_preset .set (name )
        self ._update_command_preview ()

    def _reset_preset (self ):
        # uncheck all flags and clear args
        for v in self .flags .values ():
            try :
                v .set (False )
            except Exception :
                pass 
        for v in self .flag_args .values ():
            try :
                v .set ("")
            except Exception :
                pass 
        self .preset_name .set ("")
        self ._update_command_preview ()

    def _profile_save (self ):
        name =self .profile_name .get ().strip ()
        if not name :
            messagebox .showwarning ("Profile","Please enter a profile name")
            return 
        self .profiles [name ]={
        "iphone_ip":self .iphone_ip .get (),
        "iphone_port":int (self .iphone_port .get ()or 22 ),
        "username":self .username .get (),
        "use_password":bool (self .use_password .get ()),
        "private_key_path":self .private_key_path .get (),
        }
        try :
            self .profile_combo ['values']=sorted (list (self .profiles .keys ()))
        except Exception :
            pass 
        self ._save_settings ()

    def _profile_load (self ):
        name =self .profile_name .get ().strip ()
        prof =self .profiles .get (name )
        if not prof :
            messagebox .showwarning ("Profile","Profile not found")
            return 
        self .iphone_ip .set (prof .get ("iphone_ip",self .iphone_ip .get ()))
        self .iphone_port .set (int (prof .get ("iphone_port",self .iphone_port .get ()or 22 )))
        self .username .set (prof .get ("username",self .username .get ()))
        self .use_password .set (bool (prof .get ("use_password",self .use_password .get ())))
        self .private_key_path .set (prof .get ("private_key_path",self .private_key_path .get ()))
        self ._apply_validation ()

    def _profile_delete (self ):
        name =self .profile_name .get ().strip ()
        if not name or name not in self .profiles :
            return 
        try :
            del self .profiles [name ]
        except Exception :
            pass 
        try :
            self .profile_combo ['values']=sorted (list (self .profiles .keys ()))
        except Exception :
            pass 
        self ._save_settings ()

    # -----------------------------
    # basic tooltip helper
    # -----------------------------
    def _add_tooltip (self ,widget ,text :str ):
        tip ={'tw':None }
        def enter (_):
            try :
                if tip ['tw'] is not None :
                    return 
                x =widget .winfo_rootx ()+20 
                y =widget .winfo_rooty ()+20 
                tw =tk .Toplevel (widget )
                tw .wm_overrideredirect (True )
                tw .wm_geometry (f"+{x}+{y}")
                lbl =ttk .Label (tw ,text =text ,background ="#FFFFE0" ,relief ="solid" ,borderwidth =1 )
                lbl .pack (ipadx =4 ,ipady =2 )
                tip ['tw']=tw 
            except Exception :
                pass 
        def leave (_):
            try :
                if tip ['tw'] is not None :
                    tip ['tw'].destroy ()
                    tip ['tw']=None 
            except Exception :
                pass 
        widget .bind ("<Enter>",enter )
        widget .bind ("<Leave>",leave )

    def _choose_app_dir (self ):
        path =filedialog .askdirectory (title ="Select .app folder")
        if path :
            self .app_dir_path .set (path )
            self ._add_history (self ._appdir_history ,path )
            self ._refresh_combos ()

    def _choose_remote_output (self ,var ):
    # for -o argument documentation clarity this is a remote path on device
    # we cannot show remote folder picker easily so we assist with a common path
        var .set ("/var/mobile/Documents/")

    def _log (self ,text ):
        # make the output read-only except when appending
        self .output .configure (state =tk .NORMAL )
        try :
            self ._append_colored (self .output ,text )
        except Exception :
            self .output .insert (tk .END ,text +"\n")
        self .output .see (tk .END )
        self .output .configure (state =tk .DISABLED )

    def _clear_output (self ):
        try :
            self .output .configure (state =tk .NORMAL )
            self .output .delete ("1.0",tk .END )
        finally :
            self .output .configure (state =tk .DISABLED )

    def _jf_log (self ,text :str ):
        def do ():
            try :
                self .jf_output .configure (state =tk .NORMAL )
                try :
                    self ._append_colored (self .jf_output ,text )
                except Exception :
                    self .jf_output .insert (tk .END ,text +"\n")
                self .jf_output .see (tk .END )
            finally :
                self .jf_output .configure (state =tk .DISABLED )
        self .after (0 ,do )

    def _append_colored (self ,widget ,text :str ):
        # simple heuristics to colorize ls-like output and common paths
        # splits on lines, applies tags when detected
        lines =str (text ).splitlines ()or [""]
        for line in lines :
            applied =False 
            stripped =line .strip ()
            # ls -l style: permission char first
            if stripped [:1 ]in ['d','-','l'] and len (stripped )>10 and ' ' in stripped :
                parts =stripped .split ()
                name =parts [-1 ]if parts else stripped 
                if stripped .startswith ('d') or name .endswith ('/'):
                    widget .insert (tk .END ,line +"\n",('dir',))
                    applied =True 
                elif 'x' in parts [0 ]:
                    widget .insert (tk .END ,line +"\n",('exec',))
                    applied =True 
            # directories in plain ls often end with /
            if not applied and stripped .endswith ('/'):
                widget .insert (tk .END ,line +"\n",('dir',))
                applied =True 
            # highlight Applications or *.app bundles
            if not applied and ('/Applications' in stripped or ' Applications' in stripped or stripped .endswith ('.app') or '.app/' in stripped ):
                widget .insert (tk .END ,line +"\n",('app',))
                applied =True 
            # color common path-looking strings
            if not applied and ('/' in stripped or '\\' in stripped ):
                widget .insert (tk .END ,line +"\n",('path',))
                applied =True 
            # warnings/errors
            low =stripped .lower ()
            if not applied and (low .startswith ('warning') or ' warn ' in f' {low} '):
                widget .insert (tk .END ,line +"\n",('warn',))
                applied =True 
            if not applied and (low .startswith ('error') or ' failed' in low or ' not found' in low ):
                widget .insert (tk .END ,line +"\n",('error',))
                applied =True 
            if not applied :
                widget .insert (tk .END ,line +"\n")

        # ssh helpers
    def _connect (self ):
        if paramiko is None :
            raise RuntimeError ("Paramiko not installed. Please install dependencies from requirements.txt")
        ip =self .iphone_ip .get ().strip ()
        if not ip :
            raise ValueError ("iPhone IP is required")
        port =int (self .iphone_port .get ()or 22 )
        username =self .username .get ().strip ()or 'root'

        client =paramiko .SSHClient ()
        client .set_missing_host_key_policy (paramiko .AutoAddPolicy ())

        pkey_obj =None 
        key_path =self .private_key_path .get ().strip ()or None 

        tried_keys =[]
        def try_load_key (kind ):
        # maintain histories
            self ._add_history (self ._ip_history ,self .iphone_ip .get ())
            self ._add_history (self ._user_history ,self .username .get ())
            if self .private_key_path .get ():
                self ._add_history (self ._key_history ,self .private_key_path .get ())
                # try user-provided key first if any
            pkey =None 
            try :
                if kind =='RSA':
                    return paramiko .RSAKey .from_private_key_file (key_path )
                elif kind =='DSS':
                    return paramiko .DSSKey .from_private_key_file (key_path )
            except Exception as e :
                self ._log (f"Failed to load {kind} key: {e}")
                return None 

                # determine which keys to try
        kinds =[]
        if self .auth_choice .get ()=='RSA':
            kinds =['RSA']
        elif self .auth_choice .get ()=='DSS':
            kinds =['DSS']
        else :
            kinds =['RSA','DSS']

        last_error =None 
        for kind in kinds :
            pkey_obj =try_load_key (kind )
            tried_keys .append (kind )
            try :
                if pkey_obj is not None :
                    client .connect (ip ,port =port ,username =username ,pkey =pkey_obj ,timeout =15 ,allow_agent =False ,look_for_keys =False )
                    if not self .commands_only .get ():
                        self ._log (f"Connected with {kind} key.")
                    return client 
            except Exception as e :
                last_error =e 
                self ._log (f"{kind} key auth failed: {e}")

                # optional password fallback
        if self .use_password .get ():
            try :
                client .connect (ip ,port =port ,username =username ,password =self .password .get (),timeout =15 ,allow_agent =False ,look_for_keys =False )
                if not self .commands_only .get ():
                    self ._log ("Connected with password.")
                return client 
            except Exception as e :
                last_error =e 
                self ._log (f"Password auth failed: {e}")

        raise RuntimeError (f"SSH connection failed. Tried keys: {tried_keys} and password={self.use_password.get()}. Last error: {last_error}")



    def _sftp_put (self ,client ,local_path ,remote_path ):
        sftp =client .open_sftp ()
        try :
        # ensure remote directory exists
            remote_dir =os .path .dirname (remote_path )
            try :
                sftp .stat (remote_dir )
            except IOError :
            # attempt to create directory path recursively simple approach
                parts =remote_dir .strip ('/').split ('/')
                cur =''
                for p in parts :
                    cur =cur +'/'+p 
                    try :
                        sftp .stat (cur )
                    except IOError :
                        try :
                            sftp .mkdir (cur )
                        except Exception :
                            pass 
            if not self .commands_only .get ():
                self ._log (f"Uploading {local_path} -> {remote_path}")
            sftp .put (local_path ,remote_path )
        finally :
            sftp .close ()

    def _exec (self ,client ,command ,raw =False ,commands_only =False ,log_fn =None ):
    # commands_only: only log command line still executes command but suppresses outputs/exit code logs
        log =log_fn or self ._log 
        if commands_only or not raw :
            log (f"$ {command}")
        stdin ,stdout ,stderr =client .exec_command (command )
        chan =stdout .channel 
        err_chan =stderr .channel 
        # stream outputs in near real-time
        out_buf =[]
        err_buf =[]
        while True :
            any_data =False 
            if chan .recv_ready ():
                data =chan .recv (4096 )
                if data :
                    any_data =True 
                    if not commands_only :
                        try :
                            text =data .decode (errors ='ignore')
                        except Exception :
                            text =str (data )
                            # log chunks as they arrive
                        log (text .rstrip ('\n'))
                    else :
                        out_buf .append (data )
            if err_chan .recv_stderr_ready ():
                datae =err_chan .recv_stderr (4096 )
                if datae :
                    any_data =True 
                    if not commands_only :
                        try :
                            texte =datae .decode (errors ='ignore')
                        except Exception :
                            texte =str (datae )
                        log (texte .rstrip ('\n'))
                    else :
                        err_buf .append (datae )
            if chan .exit_status_ready ()and not chan .recv_ready ()and not err_chan .recv_stderr_ready ():
                break 
            if not any_data :
                time .sleep (0.05 )
        rc =chan .recv_exit_status ()
        if not commands_only and not raw :
            log (f"[exit {rc}]")
        return rc 

    def _ps_quote (self ,s :str )->str :
    # single-quote for powershell escape embedded single quotes by doubling them
        return "'"+(s .replace ("'","''"))+"'"

    def _on_appdrop_install (self ):
        self ._run_with_icon_anim (self ._appdrop_install_flow )

    def _on_clean_leftovers (self ):
        self ._run_with_icon_anim (self ._clean_leftovers_flow )

    def _on_uicache_mobile (self ):
        self ._run_with_icon_anim (self ._uicache_mobile_flow )

    def _on_install_deb (self ):
        self ._run_with_icon_anim (self ._install_deb_flow )

    def _on_install_deb_url (self ):
        self ._run_with_icon_anim (self ._install_deb_url_flow )

    def _on_uninstall_deb (self ):
        self ._run_with_icon_anim (self ._uninstall_deb_flow )

    def _on_save_jf_output (self ):
        try :
            path =filedialog .asksaveasfilename (title ="Save JAILFR3E Output",defaultextension =".log",filetypes =[["Log files","*.log"],["Text files","*.txt"],["All files","*.*"]])
            if not path :
                return 
                # temporarily enable to read content
            self .jf_output .configure (state =tk .NORMAL )
            data =self .jf_output .get ("1.0",tk .END )
            self .jf_output .configure (state =tk .DISABLED )
            with open (path ,'w',encoding ='utf-8')as f :
                f .write (data )
            messagebox .showinfo ("Save Output",f"Saved to {path}")
        except Exception as e :
            messagebox .showerror ("Save Output",f"Failed: {e}")

            # -----------------------------
            # batch install jailfr3e
            # -----------------------------
    def _app_display_name (self ,app_dir :str ):
        # read display name from info.plist fallback to folder name
        try :
            plist_path =os .path .join (app_dir ,'Info.plist')
            if os .path .isfile (plist_path ):
                with open (plist_path ,'rb')as f :
                    info =plistlib .load (f )
                name =info .get ('CFBundleDisplayName') or info .get ('CFBundleName')
                if isinstance (name ,str )and name .strip ():
                    return name .strip ()
        except Exception :
            pass 
        return os .path .basename (app_dir .rstrip (os .sep ))

    def _on_batch_jf_ipas (self ):
    # pick multiple ipa files
        paths =filedialog .askopenfilenames (title ="Select IPA files for batch install",filetypes =[("IPA files","*.ipa"),("All files","*.*")])
        if not paths :
            return 
            # capture list tuple to a python list
        ipa_list =[p for p in paths if p and os .path .isfile (p )]
        if not ipa_list :
            messagebox .showerror ("Batch Install","No valid IPA files selected.")
            return 
        def run ():
            self ._jf_log (f"Batch JAILFR3E: {len(ipa_list)} IPAs")
            ok =0 
            for idx ,ipa in enumerate (ipa_list ,1 ):
                try :
                    self ._jf_log (f"[{idx}/{len(ipa_list)}] Installing {os.path.basename(ipa)} …")
                    self .ipa_path .set (ipa )
                    self ._add_history (self ._ipa_history ,ipa )
                    self ._jailfree_install_flow ()
                    ok +=1 
                except Exception as e :
                    self ._jf_log (f"Batch item failed: {e}")
            self ._jf_log (f"Batch finished: {ok}/{len(ipa_list)} succeeded.")
        self ._run_with_icon_anim (run )

    def _on_batch_appdrop (self ):
    # ask for a parent folder containing one or more app directories
        base =filedialog .askdirectory (title ="Select folder containing .app bundles")
        if not base :
            return 
        if not os .path .isdir (base ):
            messagebox .showerror ("Batch AppDrop","Selected path is not a directory.")
            return 
            # find app directories scan depth 2
        app_dirs =[]
        try :
            for root ,dirs ,files in os .walk (base ):
                for d in list (dirs ):
                    if d .lower ().endswith ('.app'):
                        app_dirs .append (os .path .join (root ,d ))
                        # only scan one level deep from base for performance/readability
                if root !=base :
                # prevent deep recursion remove subdirs from further walk
                    dirs [:]=[]
        except Exception :
            pass 
        if not app_dirs :
            messagebox .showinfo ("Batch AppDrop","No .app bundles found under the selected folder.")
            return 
        def run ():
            self ._jf_log (f"Batch AppDrop: {len(app_dirs)} .app bundles")
            try :
                names =[self ._app_display_name (a )for a in app_dirs ]
                if names :
                    self ._jf_log ("Ready to batch install: "+", ".join (names ))
            except Exception :
                pass 
            ok =0 
            for idx ,adir in enumerate (app_dirs ,1 ):
                try :
                    name =self ._app_display_name (adir )
                    self ._jf_log (f"[{idx}/{len(app_dirs)}] Installing {name} …")
                    self .app_dir_path .set (adir )
                    # ensure ipa is not used as a fallback
                    self .ipa_path .set ("")
                    self ._add_history (self ._appdir_history ,adir )
                    self ._appdrop_install_flow ()
                    ok +=1 
                except Exception as e :
                    self ._jf_log (f"Batch item failed: {e}")
            self ._jf_log (f"Batch finished: {ok}/{len(app_dirs)} succeeded.")
        self ._run_with_icon_anim (run )

        # -----------------------------
        # drag-and-drop helpers jailfr3e
        # -----------------------------
    def _parse_dnd_files (self ,data :str ):
    # data can be like: {c:\\path with spaces\\fileipa} or c:\\file1ipa c:\\file2ipa
        files =[]
        cur =''
        in_brace =False 
        for ch in data :
            if ch =='{':
                in_brace =True 
                cur =''
            elif ch =='}':
                in_brace =False 
                files .append (cur )
                cur =''
            elif ch ==' 'and not in_brace :
                if cur :
                    files .append (cur )
                    cur =''
            else :
                cur +=ch 
        if cur :
            files .append (cur )
            # normalize and filter
        return [f .strip ().strip ('\u0000')for f in files if f and f .strip ()]

    def _on_jf_drop (self ,event ):
        try :
            paths =self ._parse_dnd_files (getattr (event ,'data','')or '')
            if not paths :
                return 
            p =paths [0 ]
            if os .path .isdir (p ):
            # dropped folder -> appdrop
                self .app_dir_path .set (p )
                self ._add_history (self ._appdir_history ,p )
            elif os .path .isfile (p )and p .lower ().endswith ('.ipa'):
            # dropped ipa -> ipa selection
                self .ipa_path .set (p )
                self ._add_history (self ._ipa_history ,p )
            self ._refresh_combos ()
        except Exception as e :
        # non-fatal keep ui responsive
            try :
                self ._jf_log (f"DnD error: {e}")
            except Exception :
                pass 

    def _appdrop_install_flow (self ):
        try :
            app_dir =self .app_dir_path .get ().strip ()
            ipa =self .ipa_path .get ().strip ()
            tmpdir =tempfile .mkdtemp (prefix ="ix_ad_")
            cleanup_app_dir =False 
            try :
                if not app_dir or not os .path .isdir (app_dir ):
                # fallback: extract from ipa
                    if not ipa or not os .path .isfile (ipa ):
                        messagebox .showerror ("Error","Select a .app folder or a valid .ipa file")
                        return 
                    self ._add_history (self ._ipa_history ,ipa )
                    with zipfile .ZipFile (ipa ,'r')as z :
                        names =[n for n in z .namelist ()if n .startswith ('Payload/')and n .endswith ('.app/')]
                        if not names :
                            messagebox .showerror ("Error","Could not locate .app in IPA (Payload/)")
                            return 
                        app_prefix =names [0 ]
                        self ._jf_log (f"Extracting {app_prefix} from IPA...")
                        for n in z .namelist ():
                            if n .startswith (app_prefix ):
                                z .extract (n ,path =tmpdir )
                        app_dir =os .path .join (tmpdir ,app_prefix .replace ('/',os .sep ).rstrip (os .sep ))
                        cleanup_app_dir =True 
                        # zip the app directory using python zipfile more reliable than compress-archive
                app_dir_name =os .path .basename (app_dir .rstrip (os .sep ))
                app_base =app_dir_name [:-4 ]if app_dir_name .lower ().endswith ('.app')else app_dir_name 
                zip_local =os .path .join (tmpdir ,f"{app_base}.zip")
                self ._jf_log (f"Creating ZIP via Python: {zip_local}")
                try :
                    with zipfile .ZipFile (zip_local ,'w',compression =zipfile .ZIP_DEFLATED )as zf :
                        root_len =len (os .path .dirname (app_dir .rstrip (os .sep )))
                        for base ,dirs ,files in os .walk (app_dir ):
                        # preserve directory structure
                            rel_dir =base [root_len :].lstrip (os .sep ).replace (os .sep ,'/')
                            if rel_dir and not rel_dir .endswith ('/'):
                                rel_dir =rel_dir +'/'
                                # write directory entries optional in zip but keeps empty dirs
                            if rel_dir :
                                zi =zipfile .ZipInfo (rel_dir )
                                zf .writestr (zi ,'')
                            for f in files :
                                lp =os .path .join (base ,f )
                                # compute relative path inside zip under top-level folder
                                arcname =os .path .join (rel_dir ,f ).replace ('\\','/')
                                try :
                                    zf .write (lp ,arcname )
                                except Exception as ex :
                                    self ._jf_log (f"Zip warn: skip {lp}: {ex}")
                                    # verify zip exists and non-empty
                    if not os .path .exists (zip_local )or os .path .getsize (zip_local )==0 :
                        raise RuntimeError ("ZIP not created or empty")
                except Exception as ex :
                    self ._jf_log (f"Zip error: {ex}")
                client =self ._connect ()
                try :
                    remote_zip =f"/var/mobile/{app_base}.zip"
                    self ._jf_log (f"Uploading {zip_local} -> {remote_zip} via SFTP…")
                    self ._sftp_put (client ,zip_local ,remote_zip )
                    # optional: quick free space check for visibility
                    self ._jf_log ("Checking free space (df -h)...")
                    _ =self ._exec (client ,"df -h /var/mobile /Applications /var/jb/Applications 2>/dev/null || df -h",raw =self .raw_output .get (),commands_only =self .commands_only .get (),log_fn =self ._jf_log )
                    # run remote steps
                    post_step =""
                    if not self .no_respring .get ():
                        post_step =(
                        f" && (killall SpringBoard || true) && "
                        f"(if [ -x /usr/bin/uicache ]; then UC=/usr/bin/uicache; else UC=uicache; fi; su mobile -c \"$UC\" || sudo -u mobile \"$UC\")"
                        )
                    chained =(
                    f"cd /var/mobile && "
                    f"if [ -d /var/jb/Applications ]; then DEST=/var/jb/Applications; else DEST=/Applications; fi; "
                    f"unzip -o {self._shell_quote(app_base + '.zip')}; rc=$?; if [ $rc -ne 0 ] && [ $rc -ne 1 ]; then exit $rc; fi; "
                    f"rm -f {self._shell_quote(app_base + '.zip')} && "
                    f"mv {self._shell_quote(app_dir_name)} \"$DEST\"/ && "
                    f"chmod -R 755 \"$DEST\"/{self._shell_quote(app_dir_name)} && "
                    f"chown -R mobile:mobile \"$DEST\"/{self._shell_quote(app_dir_name)}"+post_step 
                    )
                    rc =self ._exec (client ,chained ,raw =self .raw_output .get (),commands_only =self .commands_only .get (),log_fn =self ._jf_log )
                finally :
                    try :
                        client .close ()
                    except Exception :
                        pass 
            finally :
                if cleanup_app_dir :
                    try :
                        shutil .rmtree (app_dir ,ignore_errors =True )
                    except Exception :
                        pass 
                shutil .rmtree (tmpdir ,ignore_errors =True )
        except Exception as e :
            self ._jf_log (f"Error: {e}")

    def _uicache_mobile_flow (self ):
        try :
        # execute uicache as the mobile user
            chained =(
            "if [ -x /usr/bin/uicache ]; then UC=/usr/bin/uicache; else UC=uicache; fi; "
            "(su mobile -c \"$UC\" || sudo -u mobile \"$UC\")"
            )
            ssh_cmd =[
            "ssh",
            "-o","HostKeyAlgorithms=+ssh-rsa,ssh-dss",
            "-p",str (self .iphone_port .get ()),
            f"{self.username.get()}@{self.iphone_ip.get()}",
            chained ,
            ]
            rc =self ._exec_local (ssh_cmd )
            if rc ==0 :
                messagebox .showinfo ("Extras","uicache (as mobile) executed.")
            else :
                messagebox .showerror ("Extras",f"uicache failed (exit {rc}). See Jailfree Output.")
        except Exception as e :
            self ._jf_log (f"Error: {e}")

    def _install_deb_flow (self ):
        try :
        # pick a local deb file
            path =filedialog .askopenfilename (title ="Select .deb file",filetypes =[("DEB packages","*.deb"),("All files","*.*")])
            if not path :
                return 
            if not os .path .isfile (path ):
                messagebox .showerror ("Extras","Selected file does not exist.")
                return 
            client =self ._connect ()
            try :
                remote_path =f"/var/root/"+os .path .basename (path )
                # upload deb to device
                self ._jf_log (f"Uploading {path} -> {remote_path}")
                self ._sftp_put (client ,path ,remote_path )
                # install via dpkg then fix depends
                cmds =[
                f"dpkg -i {self._shell_quote(remote_path)}",
                "apt-get -f install -y || true",
                ]
                last_rc =0 
                for c in cmds :
                    rc =self ._exec (client ,c ,raw =self .raw_output .get (),commands_only =self .commands_only .get (),log_fn =self ._jf_log )
                    last_rc =rc 
                if last_rc ==0 :
                    messagebox .showinfo ("DEB Install","Install finished. You may need to respring.")
                else :
                    messagebox .showerror ("DEB Install",f"Install finished with exit {last_rc}. See Jailfree Output.")
            finally :
                try :
                    client .close ()
                except Exception :
                    pass 
        except Exception as e :
            self ._jf_log (f"Error: {e}")

    def _install_deb_url_flow (self ):
        try :
            url =simpledialog .askstring ("Install .deb from URL","Enter URL to .deb:")
            if not url :
                return 
                # download to temp
            fd ,local_tmp =tempfile .mkstemp (suffix =".deb")
            os .close (fd )
            try :
                self ._jf_log (f"Downloading {url} ...")
                urllib .request .urlretrieve (url ,local_tmp )
                # reuse local install flow upload/install
                path =local_tmp 
                client =self ._connect ()
                try :
                    remote_path =f"/var/root/"+os .path .basename (path )
                    self ._jf_log (f"Uploading {path} -> {remote_path}")
                    self ._sftp_put (client ,path ,remote_path )
                    cmds =[
                    f"dpkg -i {self._shell_quote(remote_path)}",
                    "apt-get -f install -y || true",
                    ]
                    last_rc =0 
                    for c in cmds :
                        rc =self ._exec (client ,c ,raw =self .raw_output .get (),commands_only =self .commands_only .get (),log_fn =self ._jf_log )
                        last_rc =rc 
                    if last_rc ==0 :
                        messagebox .showinfo ("DEB Install","Install finished. You may need to respring.")
                    else :
                        messagebox .showerror ("DEB Install",f"Install finished with exit {last_rc}. See Jailfree Output.")
                finally :
                    try :
                        client .close ()
                    except Exception :
                        pass 
            finally :
                try :
                    os .remove (local_tmp )
                except Exception :
                    pass 
        except Exception as e :
            self ._jf_log (f"Error: {e}")

    def _uninstall_deb_flow (self ):
        try :
            pkg =simpledialog .askstring ("Uninstall package","Enter package id (e.g. com.example.pkg):")
            if not pkg :
                return 
            client =self ._connect ()
            try :
                rc =self ._exec (client ,f"dpkg -r {self._shell_quote(pkg)}",raw =self .raw_output .get (),commands_only =self .commands_only .get (),log_fn =self ._jf_log )
                if rc ==0 :
                    messagebox .showinfo ("Uninstall","Package removal finished. You may need to respring.")
                else :
                    messagebox .showerror ("Uninstall",f"Removal finished with exit {rc}. See Jailfree Output.")
            finally :
                try :
                    client .close ()
                except Exception :
                    pass 
        except Exception as e :
            self ._jf_log (f"Error: {e}")

    def _on_close (self ):
        try :
            self ._save_settings ()
        except Exception :
            pass 
            # cleanup temp icon frames
        try :
            if getattr (self ,"_icon_tempdir",None ):
                shutil .rmtree (self ._icon_tempdir ,ignore_errors =True )
        except Exception :
            pass 
        self .destroy ()

    def _settings_path (self ):
        try :
            base =os .path .expanduser ("~/.iSync")
            os .makedirs (base ,exist_ok =True )
            return os .path .join (base ,"settings.json")
        except Exception :
            return os .path .join (os .getcwd (),"isync_settings.json")

    def _load_settings (self ):
        p =self ._settings_path ()
        if not os .path .exists (p ):
            return 
        with open (p ,'r',encoding ='utf-8')as f :
            data =json .load (f )
            # histories
        self ._ip_history [:]=data .get ('ip_history',self ._ip_history )
        self ._user_history [:]=data .get ('user_history',self ._user_history )
        self ._key_history [:]=data .get ('key_history',self ._key_history )
        self ._ipa_history [:]=data .get ('ipa_history',self ._ipa_history )
        self ._appdir_history [:]=data .get ('appdir_history',self ._appdir_history )
        # last selections
        self .iphone_ip .set (data .get ('iphone_ip',self .iphone_ip .get ()))
        self .iphone_port .set (data .get ('iphone_port',self .iphone_port .get ()))
        self .username .set (data .get ('username',self .username .get ()))
        self .private_key_path .set (data .get ('private_key_path',self .private_key_path .get ()))
        self .ipa_path .set (data .get ('ipa_path',self .ipa_path .get ()))
        self .app_dir_path .set (data .get ('app_dir_path',self .app_dir_path .get ()))
        self .no_respring .set (bool (data .get ('no_respring',False )))
        # apply to combos
        self ._refresh_combos ()

    def _save_settings (self ):
        data ={
        'ip_history':self ._ip_history ,
        'user_history':self ._user_history ,
        'key_history':self ._key_history ,
        'ipa_history':self ._ipa_history ,
        'appdir_history':self ._appdir_history ,
        'iphone_ip':self .iphone_ip .get (),
        'iphone_port':int (self .iphone_port .get ()or 22 ),
        'username':self .username .get (),
        'private_key_path':self .private_key_path .get (),
        'ipa_path':self .ipa_path .get (),
        'app_dir_path':self .app_dir_path .get (),
        'no_respring':bool (self .no_respring .get ()),
        }
        p =self ._settings_path ()
        with open (p ,'w',encoding ='utf-8')as f :
            json .dump (data ,f ,indent =2 )

    def _clean_leftovers_flow (self ):
        try :
        # derive app_dir_name and app_base from current selections
            app_dir =(self .app_dir_path .get ()or '').strip ()
            ipa =(self .ipa_path .get ()or '').strip ()
            app_dir_name =None 
            app_base =None 
            if app_dir and os .path .isdir (app_dir ):
                app_dir_name =os .path .basename (app_dir .rstrip (os .sep ))
            elif ipa and os .path .isfile (ipa ):
                try :
                    with zipfile .ZipFile (ipa ,'r')as z :
                        names =[n for n in z .namelist ()if n .startswith ('Payload/')and n .endswith ('.app/')]
                        if names :
                            app_dir_name =os .path .basename (names [0 ].rstrip ('/'))
                except Exception :
                    pass 
            if app_dir_name :
                app_base =app_dir_name [:-4 ]if app_dir_name .lower ().endswith ('.app')else app_dir_name 
            else :
            # fallback: do nothing with app dir only attempt zip cleanup if ipa name available
                if ipa :
                    base =os .path .splitext (os .path .basename (ipa ))[0 ]
                    app_base =base 
            if not app_base and not app_dir_name :
                messagebox .showerror ("Extras","Could not infer app name. Select a .app or IPA first.")
                return 
            client =self ._connect ()
            try :
            # build chained cleanup command
                parts =["cd /var/mobile"]
                if app_base :
                    parts .append (f"rm -f {self._shell_quote(app_base + '.zip')}")
                parts .append ("if [ -d /var/jb/Applications ]; then DEST=/var/jb/Applications; else DEST=/Applications; fi")
                if app_dir_name :
                    parts .append (f"rm -rf \"$DEST\"/{self._shell_quote(app_dir_name)}")
                chained =" && ".join (parts )
                rc =self ._exec (client ,chained ,raw =self .raw_output .get (),commands_only =self .commands_only .get (),log_fn =self ._jf_log )
                if rc ==0 :
                    messagebox .showinfo ("Extras","Leftovers cleaned.")
                else :
                    messagebox .showerror ("Extras",f"Cleanup failed (exit {rc}). See Jailfree Output.")
            finally :
                try :
                    client .close ()
                except Exception :
                    pass 
        except Exception as e :
            self ._jf_log (f"Error: {e}")

    def _exec_local (self ,cmd_list ):
        """Run a local command (list form) and stream stdout/stderr to Jailfree log. Returns exit code."""
        try :
            import subprocess 
            self ._jf_log ("$ "+" ".join (cmd_list ))
            p =subprocess .Popen (cmd_list ,stdout =subprocess .PIPE ,stderr =subprocess .STDOUT ,bufsize =1 ,text =True )
            assert p .stdout is not None 
            for line in p .stdout :
                self ._jf_log ("PowerShell: "+line .rstrip ("\n"))
            p .wait ()
            self ._jf_log (f"PowerShell: [exit {p.returncode}]")
            return p .returncode 
        except FileNotFoundError as e :
            self ._jf_log (f"PowerShell: Local command not found: {cmd_list[0]}")
            return 127 
        except Exception as e :
            self ._jf_log (f"PowerShell: Local exec error: {e}")
            return 1 

    def _on_jailfree_install (self ):
        threading .Thread (target =self ._jailfree_install_flow ,daemon =True ).start ()

    def _jailfree_install_flow (self ):
        try :
            ipa =self .ipa_path .get ().strip ()
            if not ipa or not os .path .isfile (ipa ):
                messagebox .showerror ("Error","Select a valid .ipa file")
                return 
            self ._add_history (self ._ipa_history ,ipa )
            tmpdir =tempfile .mkdtemp (prefix ="ix_jf_")
            app_dir_local =None 
            try :
            # extract app from ipa zip
                with zipfile .ZipFile (ipa ,'r')as z :
                # find payload/<appname>app/
                    app_prefix =None 
                    for n in z .namelist ():
                        if n .startswith ('Payload/')and n .endswith ('.app/'):
                            app_prefix =n 
                            break 
                    if not app_prefix :
                    # some zips may not include trailing slash dirs infer from files
                        for n in z .namelist ():
                            if n .startswith ('Payload/')and '.app/'in n :
                                app_prefix =n .split ('.app/')[0 ]+'.app/'
                                break 
                    if not app_prefix :
                        messagebox .showerror ("Error","Could not locate .app in IPA (looking under Payload/)")
                        return 
                    if not self .commands_only .get ():
                        self ._jf_log (f"Extracting {app_prefix} from IPA...")
                    for n in z .namelist ():
                        if n .startswith (app_prefix ):
                            z .extract (n ,path =tmpdir )
                    app_dir_local =os .path .join (tmpdir ,app_prefix )
                    # connect and ensure destination
                client =self ._connect ()
                try :
                    remote_app_path ="/var/mobile/"+app_prefix # payload/<appname>app/
                    remote_app_path =remote_app_path .rstrip ('/')
                    # ensure base dir exists
                    self ._exec (
                    client ,
                    "mkdir -p /var/mobile/Payload",
                    raw =self .raw_output .get (),
                    commands_only =self .commands_only .get (),
                    log_fn =self ._jf_log 
                    )
                    # upload recursively
                    if not self .commands_only .get ():
                        self ._jf_log (f"Uploading .app to {remote_app_path} ...")
                    self ._sftp_upload_dir (client ,app_dir_local ,remote_app_path )
                    # fix ownership
                    self ._exec (
                    client ,
                    f"chown -R mobile:mobile {self._shell_quote(remote_app_path)}",
                    raw =self .raw_output .get (),
                    commands_only =self .commands_only .get (),
                    log_fn =self ._jf_log 
                    )
                    # respring then uicache as mobile
                    self ._exec (client ,"su mobile -c 'killall SpringBoard'",raw =self .raw_output .get (),commands_only =self .commands_only .get (),log_fn =self ._jf_log )
                    self ._exec (client ,"su mobile -c 'uicache'",raw =self .raw_output .get (),commands_only =self .commands_only .get (),log_fn =self ._jf_log )
                    if not self .commands_only .get ()and not self .raw_output .get ():
                        self ._jf_log ("Done! If you don't see the app, try rebooting.")
                finally :
                    client .close ()
            finally :
                try :
                    shutil .rmtree (tmpdir ,ignore_errors =True )
                except Exception :
                    pass 
        except Exception as e :
            if not self .commands_only .get ():
                self ._jf_log (f"Error: {e}")

    def _sftp_upload_dir (self ,client ,local_dir ,remote_dir ):
        """Recursively upload a local directory to remote_dir using SFTP."""
        sftp =client .open_sftp ()
        try :
        # create root
            try :
                sftp .stat (remote_dir )
            except IOError :
            # recursively create
                parts =remote_dir .strip ('/').split ('/')
                cur =''
                for p in parts :
                    cur =cur +'/'+p 
                    try :
                        sftp .stat (cur )
                    except IOError :
                        try :
                            sftp .mkdir (cur )
                        except Exception :
                            pass 
            for root ,dirs ,files in os .walk (local_dir ):
                rel =os .path .relpath (root ,local_dir ).replace ('\\','/')
                rdir =remote_dir if rel =='.'else f"{remote_dir}/{rel}"
                # ensure directory exists
                try :
                    sftp .stat (rdir )
                except IOError :
                    try :
                        sftp .mkdir (rdir )
                    except Exception :
                        pass 
                for d in dirs :
                    rd =f"{rdir}/{d}"
                    try :
                        sftp .stat (rd )
                    except IOError :
                        try :
                            sftp .mkdir (rd )
                        except Exception :
                            pass 
                for f in files :
                    lp =os .path .join (root ,f )
                    rp =f"{rdir}/{f}"
                    sftp .put (lp ,rp )
        finally :
            sftp .close ()

            # actions
    def _on_install_click (self ):
        self ._run_with_icon_anim (self ._install_flow )

    def _on_run_ipainstaller_only (self ):
        self ._run_with_icon_anim (self ._run_ipainstaller_only_flow )

    def _on_peek_root (self ):
        self ._run_with_icon_anim (self ._peek_root_flow )

    def _on_respring (self ):
        self ._run_with_icon_anim (self ._respring_flow )

    def _on_check_appsync (self ):
        self ._run_with_icon_anim (self ._check_appsync_flow )

    def _on_install_appsync (self ):
        self ._run_with_icon_anim (self ._install_appsync_flow )

    def _collect_ipainstaller_args (self ):
        args =[]
        # order generally shouldnt matter but keep it consistent
        for fl in ['-a','-b','-B','-c','-d','-f','-h','-i','-l','-n','-o','-q','-Q','-r','-u']:
            if self .flags [fl ].get ():
                args .append (fl )
                if fl in self .flag_args and self .flag_args [fl ].get ().strip ():
                # expand multi values on space/comma for flags that accept multiple app_ids
                    val =self .flag_args [fl ].get ().strip ()
                    if fl in ('-i','-u'):
                        parts =[p for chunk in val .replace (',',' ').split (' ')if (p :=chunk .strip ())]
                        args .extend (parts )
                    else :
                        args .append (val )
        return args 

    def _install_flow (self ):
        try :
            ipa =self .ipa_path .get ().strip ()
            if not ipa or not os .path .isfile (ipa ):
                messagebox .showerror ("Error","Select a valid .ipa file")
                return 
                # record ipa in history
            self ._add_history (self ._ipa_history ,ipa )
            client =self ._connect ()
            try :
                remote_dir ="/var/mobile/ipas"
                remote_path =f"{remote_dir}/"+os .path .basename (ipa )
                # check if already present on device create dir if needed only upload when missing
                sftp =client .open_sftp ()
                try :
                    try :
                        sftp .stat (remote_path )
                        # file exists skip upload
                        if not self .commands_only .get ():
                            self ._log (f"Remote exists, skipping upload: {remote_path}")
                    except IOError :
                    # ensure directory exists then upload
                        try :
                            sftp .stat (remote_dir )
                        except IOError :
                        # create recursively
                            parts =remote_dir .strip ('/').split ('/')
                            cur =''
                            for p in parts :
                                cur =cur +'/'+p 
                                try :
                                    sftp .stat (cur )
                                except IOError :
                                    try :
                                        sftp .mkdir (cur )
                                    except Exception :
                                        pass 
                        if not self .commands_only .get ():
                            self ._log (f"Uploading {ipa} -> {remote_path}")
                        sftp .put (ipa ,remote_path )
                finally :
                    sftp .close ()

                if self .installer_choice .get ()=='ipainstaller':
                    args =self ._collect_ipainstaller_args ()
                    cmd =["ipainstaller"]+args +[remote_path ]
                    rc =self ._exec (
                    client ,
                    ' '.join (self ._shell_quote (c )for c in cmd ),
                    raw =self .raw_output .get (),
                    commands_only =self .commands_only .get ()
                    )
                else :
                # ensure appinst is available install if missing handles rootful/rootless
                # 1 attempt install/update appinst using apt-get from either rootless /var/jb or system
                    install_line =(
                    "if [ -x /var/jb/usr/bin/apt-get ]; then "
                    "/var/jb/usr/bin/apt-get update && /var/jb/usr/bin/apt-get install -y appinst; "
                    "else apt-get update && apt-get install -y appinst; fi"
                    )
                    self ._exec (
                    client ,
                    install_line ,
                    raw =self .raw_output .get (),
                    commands_only =self .commands_only .get ()
                    )
                    # 2 run appinst with the remote ipa path prefer path appinst else fallback to /var/jb path
                    run_line =(
                    "if command -v appinst >/dev/null 2>&1; then "
                    f"appinst {self._shell_quote(remote_path)}; "
                    "elif [ -x /var/jb/usr/bin/appinst ]; then "
                    f"/var/jb/usr/bin/appinst {self._shell_quote(remote_path)}; "
                    "else echo 'appinst not found after install attempt' 1>&2; fi"
                    )
                    self ._exec (
                    client ,
                    run_line ,
                    raw =self .raw_output .get (),
                    commands_only =self .commands_only .get ()
                    )
            finally :
                client .close ()
        except Exception as e :
            if not self .commands_only .get ():
                self ._log (f"Error: {e}")

    def _run_ipainstaller_only_flow (self ):
        try :
            client =self ._connect ()
            try :
                args =self ._collect_ipainstaller_args ()
                if not args :
                # if no flags default to showing usage
                    args =['-h']
                cmd =["ipainstaller"]+args 
                rc =self ._exec (client ,' '.join (self ._shell_quote (c )for c in cmd ),raw =self .raw_output .get ())
            finally :
                client .close ()
        except Exception as e :
            self ._log (f"Error: {e}")

    def _install_appsync_flow (self ):
        url ="https://github.com/akemin-dayo/AppSync/releases/download/116.0/ai.akemi.appsyncunified_116.0_iphoneos-arm.akemi-git-235aca6cddfbdc9fa87fcb5b2aec2df37ed6d65a.deb"
        local_tmp =None 
        try :
        # download deb to local temp
            fd ,local_tmp =tempfile .mkstemp (suffix =".deb")
            os .close (fd )
            if not self .commands_only .get ():
                self ._log (f"Downloading AppSync from {url}")
            urllib .request .urlretrieve (url ,local_tmp )

            client =self ._connect ()
            try :
                remote_path =f"/var/root/"+os .path .basename (local_tmp )
                # upload deb
                if not self .commands_only .get ():
                    self ._log (f"Uploading {local_tmp} -> {remote_path}")
                self ._sftp_put (client ,local_tmp ,remote_path )
                # install via dpkg then fix depends if needed
                cmds =[
                f"dpkg -i {self._shell_quote(remote_path)}",
                "apt-get -f install -y || true",
                ]
                for c in cmds :
                    self ._exec (
                    client ,
                    c ,
                    raw =self .raw_output .get (),
                    commands_only =self .commands_only .get ()
                    )
                if not self .commands_only .get ()and not self .raw_output .get ():
                    self ._log ("If installation succeeded, please respring. Use Tools → Respring.")
            finally :
                client .close ()
        except Exception as e :
            if not self .commands_only .get ():
                self ._log (f"Error: {e}")
        finally :
            if local_tmp and os .path .exists (local_tmp ):
                try :
                    os .remove (local_tmp )
                except Exception :
                    pass 

    def _peek_root_flow (self ):
        try :
            client =self ._connect ()
            try :
                self ._exec (client ,'ls -al /')
            finally :
                client .close ()
        except Exception as e :
            self ._log (f"Error: {e}")

    def _respring_flow (self ):
        try :
            client =self ._connect ()
            try :
                self ._exec (client ,'killall SpringBoard')
            finally :
                client .close ()
        except Exception as e :
            self ._log (f"Error: {e}")

    def _check_appsync_flow (self ):
        try :
            client =self ._connect ()
            try :
                cmds =[
                # determine jailbreak mode
                "if [ -d /var/jb ]; then echo 'Jailbreak: rootless (/var/jb exists)'; else echo 'Jailbreak: rootful (/var/jb missing)'; fi",
                # kernel info
                "uname -a",
                # check dpkg entry
                "dpkg -l | grep -i appsync || echo 'No AppSync package found via dpkg'",
                # check common dylib locations rootful and rootless
                "ls -al /Library/MobileSubstrate/DynamicLibraries | grep -i appsync | cat",
                "ls -al /var/jb/Library/MobileSubstrate/DynamicLibraries | grep -i appsync | cat",
                ]
                for c in cmds :
                    self ._exec (
                    client ,
                    c ,
                    raw =self .raw_output .get (),
                    commands_only =self .commands_only .get ()
                    )
                if not self .commands_only .get ()and not self .raw_output .get ():
                    self ._log ("Tip: If AppSync appears installed but not active, try a respring and ensure you installed from https://cydia.akemi.ai appropriate for your jailbreak (rootless vs rootful).")
            finally :
                client .close ()
        except Exception as e :
            self ._log (f"Error: {e}")

    @staticmethod 
    def _shell_quote (s ):
    # simple posix-like quoting for remote shell
        if not s :
            return "''"
        if all (c .isalnum ()or c in ('@','%','+','=',':','/','-','_','.',',')for c in s ):
            return s 
        return "'"+s .replace ("'","'\\''")+"'"


if __name__ =='__main__':
    app =IPAGui ()
    app .mainloop ()
