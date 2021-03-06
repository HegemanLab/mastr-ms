MA.MenuRender = function(email) {

    var userText = 'User: ' + email;

    var tb = new Ext.Toolbar(

        {
            id: 'toolbara',
            items: [
                { xtype: 'tbbutton', text: 'Login', id: 'login', handler: MA.MenuHandler},
                { xtype: 'tbbutton', text: 'Dashboard', id: 'dashboard', handler: MA.MenuHandler},
                { xtype: 'tbbutton', text: 'Admin', id: 'admin', menu: {
                    items: [
                        {text: 'Admin Requests', id: 'admin:adminrequests', handler: MA.MenuHandler},
                        {text: 'Active User Search', id: 'admin:usersearch', handler: MA.MenuHandler},
                        {text: 'Rejected User Search', id: 'admin:rejectedUsersearch', handler: MA.MenuHandler},
                        {text: 'Deleted User Search', id: 'admin:deletedUsersearch', handler: MA.MenuHandler},
                        new Ext.menu.Separator(),
                        {text: 'Node Management', id: 'admin:nodelist', handler: MA.MenuHandler},
                        {text: 'Organisation Management', id: 'admin:orglist', handler: MA.MenuHandler}
                    ]
                    }
                },
                { xtype: 'tbbutton', text: 'Quotes', id: 'quote', menu: {
                    items: [
                        {text: 'Make an Inquiry', id: 'quote:request', handler: MA.MenuHandler},
                        {text: 'View Quote Requests', id: 'quote:list', handler: MA.MenuHandler},
                        {text: 'My Formal Quotes', id: 'quote:listFormal', handler: MA.MenuHandler},
                        {text: 'Overview List', id: 'quote:listAll', handler: MA.MenuHandler}
                    ]
                    }
                },
                { xtype: 'tbbutton', text: 'Repository', id: 'repo', menu: {
                    items: [
                        {text: 'Projects', id: 'project:list', handler: MA.MenuHandler},
                        {text: 'Clients', id: 'client:list', handler: MA.MenuHandler},
                        {text: 'Runs', id: 'run:list', handler: MA.MenuHandler},
                        {text: 'Rule Generators', id: 'rulegenerator:list', handler: MA.MenuHandler},
                        new Ext.menu.Separator(),
                        {text: 'Admin', id: 'repo:admin', handler: MA.MenuHandler}
                    ]
                    }
                },
                { xtype: 'tbbutton', text: 'Help', id: 'help', menu: {
                    items: [
                            {text: 'Screencasts', id: 'help:screencasts', menu: {
                            items: [
                                    {text: 'Requesting a Quote', id: 'help:screencasts-quoterequest', handler: MA.MenuHandler}
                                    ]
                            }
                            },
                            {text: 'Admin screencasts', id: 'helpadmin:screencasts', menu: {
                            items: [
                                    {text: 'Accepting/rejecting users', id: 'helpadmin:screencasts-authrequest', handler: MA.MenuHandler},
                                    {text: 'Forwarding a Quote Request', id: 'helpadmin:screencasts-forwardquoterequest', handler: MA.MenuHandler},
                                    {text: 'Sending a Formal Quote', id: 'helpadmin:screencasts-forwardformal', handler: MA.MenuHandler},
                                    {text: 'Replacing a Formal Quote', id: 'helpadmin:screencasts-replaceformal', handler: MA.MenuHandler}
                                    ]
                            }
                            },
                            {text: 'Contact Us', id: 'help:contactus', handler: MA.MenuHandler }
                            ]
                    }
                },

                { xtype: 'tbfill'},
                { xtype: 'tbbutton', text: userText, id: 'userMenu', menu: {
                    items: [
                        {text: 'Logout', id: 'login:processLogout', handler: MA.LogoutHandler},
                        {text: 'My Account', id: 'user:myaccount', handler: MA.MenuHandler}
                    ]
                    }
                }
            ]
        }

    );
    tb.render('toolbar');

};

MA.MenuEnsure = function() {
    if (MA.CurrentUser.IsLoggedIn) {
        MA.MenuShow();
    }
    else {
        MA.MenuHide();
    }
};

MA.MenuShow = function() {
    var isPrivileged = (MA.CurrentUser.IsAdmin || MA.CurrentUser.IsMastrAdmin || MA.CurrentUser.IsNodeRep || MA.CurrentUser.IsProjectLeader);
    Ext.BLANK_IMAGE_URL = MA.BaseUrl + 'static/ext-3.4.0/resources/images/default/s.gif';

    //disable certain menu items if the user is not an admin
    if (isPrivileged) {
        Ext.get('admin').show();
    } else {
        Ext.get('admin').hide();

    }
    Ext.getCmp('admin:nodelist').setDisabled(!MA.CurrentUser.IsAdmin);
    Ext.getCmp('admin:orglist').setDisabled(!MA.CurrentUser.IsAdmin);
    Ext.getCmp('helpadmin:screencasts').setDisabled(!MA.CurrentUser.IsAdmin);

    Ext.getCmp('admin:adminrequests').setDisabled(!(MA.CurrentUser.IsAdmin || MA.CurrentUser.IsNodeRep));
    Ext.getCmp('admin:usersearch').setDisabled(!isPrivileged);
    Ext.getCmp('admin:rejectedUsersearch').setDisabled(!(MA.CurrentUser.IsAdmin || MA.CurrentUser.IsNodeRep));
    Ext.getCmp('admin:deletedUsersearch').setDisabled(!(MA.CurrentUser.IsAdmin || MA.CurrentUser.IsNodeRep));

    Ext.getCmp('repo:admin').setDisabled(!(MA.CurrentUser.IsAdmin || MA.CurrentUser.IsMastrAdmin));
    Ext.getCmp('client:list').setDisabled(!(MA.CurrentUser.IsAdmin || MA.CurrentUser.IsMastrAdmin || MA.CurrentUser.IsProjectLeader));

    Ext.get('login').hide();
    Ext.get('dashboard').show();
    Ext.get('userMenu').show();
    Ext.getCmp('quote:list').show();
    Ext.getCmp('quote:listAll').setDisabled(!(MA.CurrentUser.IsAdmin || MA.CurrentUser.IsNodeRep));
    Ext.getCmp('quote:listFormal').show();

    if (MA.CurrentUser.IsAdmin || MA.CurrentUser.IsMastrAdmin || MA.CurrentUser.IsProjectLeader || MA.CurrentUser.IsMastrStaff) {
        Ext.get('repo').show();
    } else {
        Ext.get('repo').hide();
    }

};

MA.MenuHandler = function(item, params) {
    //we authorize every access to check for session timeout and authorization to specific pages
    //if (item.id.substr(0,4) == "help") {
        MA.ChangeMainContent(item.id, params);
    //} else {
    //    MA.Authorize(item.id);
    //}
};

MA.LogoutHandler = function() {
    window.location = "login/processLogout";
};

MA.MenuHide = function() {

    Ext.get('login').show();
    Ext.get('dashboard').hide();
    Ext.get('admin').hide();
    Ext.get('userMenu').hide();
    Ext.getCmp('quote:list').hide();
    Ext.getCmp('quote:listAll').hide();
    Ext.getCmp('quote:listFormal').hide();
    Ext.get('repo').hide();
    Ext.getCmp('helpadmin:screencasts').disable();
};
