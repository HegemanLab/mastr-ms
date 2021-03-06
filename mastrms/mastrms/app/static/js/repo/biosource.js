MA.BioSourceInit = function() {
    var expId = MA.ExperimentController.currentId();

    Ext.getCmp('organismBioSourceMicrobialFieldset').hide();
    Ext.getCmp('organismBioSourcePlantFieldset').hide();
    Ext.getCmp('organismBioSourceAnimalFieldset').hide();
    Ext.getCmp('organismBioSourceHumanFieldset').hide();

    var loader = new Ajax.Request(wsBaseUrl + 'records/biologicalsource/experiment__id/' + expId,
                                 {
                                 asynchronous: true,
                                 evalJSON: 'force',
                                 onSuccess: MA.BioLoadSuccess
                                 });

    MA.BioSourceLoad();
};

MA.BioSourceLoad = function() {
    var expId = MA.ExperimentController.currentId();
    organStore.load({ params: { experiment__id__exact: expId } });
};

MA.BioLoadSuccess = function(response) {
    MA.CurrentSingleSourceId = response.responseJSON.rows[0].id;
    Ext.getCmp('sourceType').setValue(response.responseJSON.rows[0].type);
    Ext.getCmp('sourceInfo').setValue(response.responseJSON.rows[0].information);
    Ext.getCmp('sourceNCBI').setValue(response.responseJSON.rows[0].ncbi_id);

    MA.CurrentSourceType = response.responseJSON.rows[0].type;

    //load the source info
    Ext.getCmp('sourceNCBI').enable();
    switch (MA.CurrentSourceType) {
        case 1:
            var loader = new Ajax.Request(wsBaseUrl + 'records/microbialinfo/source__id/' + MA.CurrentSingleSourceId,
                                  {
                                  asynchronous: true,
                                  evalJSON: 'force',
                                  onSuccess: MA.SourceInfoLoadSuccess
                                  });
            break;
        case 2:
            var loader = new Ajax.Request(wsBaseUrl + 'records/plantinfo/source__id/' + MA.CurrentSingleSourceId,
                                          {
                                          asynchronous: true,
                                          evalJSON: 'force',
                                          onSuccess: MA.SourceInfoLoadSuccess
                                          });
            break;
        case 3:
            var loader = new Ajax.Request(wsBaseUrl + 'records/animalinfo/source__id/' + MA.CurrentSingleSourceId,
                                          {
                                          asynchronous: true,
                                          evalJSON: 'force',
                                          onSuccess: MA.SourceInfoLoadSuccess
                                          });
            break;
        case 4:
            var loader = new Ajax.Request(wsBaseUrl + 'records/humaninfo/source__id/' + MA.CurrentSingleSourceId,
                                          {
                                          asynchronous: true,
                                          evalJSON: 'force',
                                          onSuccess: MA.SourceInfoLoadSuccess
                                          });
            break;
        default:
            Ext.getCmp('sourceNCBI').disable();
            break;
    }

    MA.SourceTypeSelect();
};

MA.SourceInfoLoadSuccess = function(response) {
    switch (MA.CurrentSourceType) {
        case 1:
            //microbial
            Ext.getCmp('microbial_genus').setValue(response.responseJSON.rows[0].genus);
            Ext.getCmp('microbial_species').setValue(response.responseJSON.rows[0].species);
            Ext.getCmp('microbial_culture').setValue(response.responseJSON.rows[0].culture_collection_id);
            Ext.getCmp('microbial_media').setValue(response.responseJSON.rows[0].media);
            Ext.getCmp('microbial_vessel').setValue(response.responseJSON.rows[0].fermentation_vessel);
            Ext.getCmp('microbial_mode').setValue(response.responseJSON.rows[0].fermentation_mode);
            Ext.getCmp('microbial_density').setValue(response.responseJSON.rows[0].innoculation_density);
            Ext.getCmp('microbial_volume').setValue(response.responseJSON.rows[0].fermentation_volume);
            Ext.getCmp('microbial_temperature').setValue(response.responseJSON.rows[0].temperature);
            Ext.getCmp('microbial_agitation').setValue(response.responseJSON.rows[0].agitation);
            Ext.getCmp('microbial_ph').setValue(response.responseJSON.rows[0].ph);
            Ext.getCmp('microbial_gastype').setValue(response.responseJSON.rows[0].gas_type);
            Ext.getCmp('microbial_flowrate').setValue(response.responseJSON.rows[0].gas_flow_rate);
            Ext.getCmp('microbial_delivery').setValue(response.responseJSON.rows[0].gas_delivery_method);
            break;
        case 2:
            //plant
            Ext.getCmp('plant_development_stage').setValue(response.responseJSON.rows[0].development_stage);
            break;
        case 3:
            //animal
            Ext.getCmp('animalGender').setValue(response.responseJSON.rows[0].sex);
            Ext.getCmp('animalAge').setValue(response.responseJSON.rows[0].age);
            Ext.getCmp('animalParentalLine').setValue(response.responseJSON.rows[0].parental_line);
            Ext.getCmp('animal_location').setValue(response.responseJSON.rows[0].location);
//            Ext.getCmp('animal_notes').setValue(response.responseJSON.rows[0].notes);
            break;
        case 4:
            //human
            Ext.getCmp('humanGender').setValue(response.responseJSON.rows[0].sex);
            Ext.getCmp('human_dob').setValue(response.responseJSON.rows[0].date_of_birth);
            Ext.getCmp('human_bmi').setValue(response.responseJSON.rows[0].bmi);
            Ext.getCmp('human_diagnosis').setValue(response.responseJSON.rows[0].diagnosis);
            Ext.getCmp('human_location').setValue(response.responseJSON.rows[0].location);
//            Ext.getCmp('human_notes').setValue(response.responseJSON.rows[0].notes);
            break;
        default:
            break;
    }
};

MA.BioSourceBlur = function(invoker) {
    MA.ExperimentController.mask.show();

    var expId = MA.ExperimentController.currentId();

    if (expId == 0) {
        MA.ExperimentDeferredInvocation = invoker;
        MA.BioSourceBlurSuccess();
    } else {
        MA.ExperimentDeferredInvocation = invoker;
        var extraParams = "";
        var sourceType, sourceInfo, sourceNCBI;

        sourceType = Ext.getCmp('sourceType').getValue();
        sourceInfo = Ext.getCmp('sourceInfo').getValue();
        sourceNCBI = Ext.getCmp('sourceNCBI').getValue();

        var src = Ext.getCmp('sourceType');
        switch (src.getValue()) {
            case 1:
                extraParams = "&genus=" + encodeURIComponent(Ext.getCmp('microbial_genus').getValue());
                extraParams += "&species=" + encodeURIComponent(Ext.getCmp('microbial_species').getValue());
                extraParams += "&culture=" + encodeURIComponent(Ext.getCmp('microbial_culture').getValue());
                extraParams += "&media=" + encodeURIComponent(Ext.getCmp('microbial_media').getValue());
                extraParams += "&vessel=" + encodeURIComponent(Ext.getCmp('microbial_vessel').getValue());
                extraParams += "&mode=" + encodeURIComponent(Ext.getCmp('microbial_mode').getValue());
                extraParams += "&density=" + encodeURIComponent(Ext.getCmp('microbial_density').getValue());
                extraParams += "&volume=" + encodeURIComponent(Ext.getCmp('microbial_volume').getValue());
                extraParams += "&temperature=" + encodeURIComponent(Ext.getCmp('microbial_temperature').getValue());
                extraParams += "&agitation=" + encodeURIComponent(Ext.getCmp('microbial_agitation').getValue());
                extraParams += "&ph=" + encodeURIComponent(Ext.getCmp('microbial_ph').getValue());
                extraParams += "&gastype=" + encodeURIComponent(Ext.getCmp('microbial_gastype').getValue());
                extraParams += "&flowrate=" + encodeURIComponent(Ext.getCmp('microbial_flowrate').getValue());
                extraParams += "&delivery=" + encodeURIComponent(Ext.getCmp('microbial_delivery').getValue());
                break;
            case 2:
                extraParams = "&development_stage=" + encodeURIComponent(Ext.getCmp('plant_development_stage').getValue());
                break;
            case 3:
                extraParams = "&sex=" + encodeURIComponent(Ext.getCmp('animalGender').getValue());
                extraParams += "&age=" + encodeURIComponent(Ext.getCmp('animalAge').getValue());
                extraParams += "&parental_line=" + encodeURIComponent(Ext.getCmp('animalParentalLine').getValue());
                extraParams += "&location=" + encodeURIComponent(Ext.getCmp('animal_location').getValue());
//                extraParams += "&notes=" + encodeURIComponent(Ext.getCmp('animal_notes').getValue());
                break;
            case 4:
                extraParams = "&sex=" + encodeURIComponent(Ext.getCmp('humanGender').getValue());
                extraParams += "&date_of_birth=" + encodeURIComponent(Ext.util.Format.date(Ext.getCmp('human_dob').getValue(), 'Y-m-d'));
                extraParams += "&bmi=" + encodeURIComponent(Ext.getCmp('human_bmi').getValue());
                extraParams += "&diagnosis=" + encodeURIComponent(Ext.getCmp('human_diagnosis').getValue());
                extraParams += "&location=" + encodeURIComponent(Ext.getCmp('human_location').getValue());
//                extraParams += "&notes=" + encodeURIComponent(Ext.getCmp('human_notes').getValue());
                break;
            default:
                break;
        }

        //this request should ask the server to rejig the single biosource that we currently permit
        var saver = new Ajax.Request(wsBaseUrl + 'updateSingleSource/' + expId + '/?type=' + encodeURIComponent(sourceType) + '&information=' + encodeURIComponent(sourceInfo) + '&ncbi_id=' + encodeURIComponent(sourceNCBI) + extraParams,
                                 {
                                 asynchronous: true,
                                 evalJSON: 'force',
                                 onSuccess: MA.BioSourceBlurSuccess
                                 });
    }

};

MA.SourceTypeSelect = function() {
    //display the appropriate fieldset
    var src = Ext.getCmp('sourceType');

    Ext.getCmp('organismBioSourceMicrobialFieldset').hide();
    Ext.getCmp('organismBioSourcePlantFieldset').hide();
    Ext.getCmp('organismBioSourceAnimalFieldset').hide();
    Ext.getCmp('organismBioSourceHumanFieldset').hide();

    Ext.getCmp('sourceNCBI').enable();
    switch (src.getValue()) {
        case 1:
            Ext.getCmp('organismBioSourceMicrobialFieldset').show();
            break;
        case 2:
            Ext.getCmp('organismBioSourcePlantFieldset').show();
            break;
        case 3:
            Ext.getCmp('organismBioSourceAnimalFieldset').show();
            break;
        case 4:
            Ext.getCmp('organismBioSourceHumanFieldset').show();
            break;
        default:
            Ext.getCmp('sourceNCBI').disable();
            break;
    }
};

MA.BioSourceBlurSuccess = function(response) {
    MA.ExperimentController.mask.hide();

    if (Ext.isDefined(response)) {
        if (!Ext.isDefined(response.responseJSON)) {
            Ext.Msg.alert('Error', 'An unexpected error has occurred. Your session may have timed out. Please reload your browser window.');
            return;
        }
    }

    var index = MA.ExperimentDeferredInvocation.index;

    if (index >= 0) {

        Ext.getCmp("expContent").getLayout().setActiveItem(index);
        Ext.currentExperimentNavItem = index;
    }

    MA.ExperimentDeferredInvocation.init();

    MA.ExperimentDeferredInvocation = {'index': -1, 'init': MA.Null};
};

MA.SaveOrganRow = function(roweditor, changes, rec, i) {
    var bundledData = {};

    bundledData.name = rec.data.name;
    bundledData.detail = rec.data.detail;
    bundledData.abbreviation = rec.data.abbreviation;

    MA.SaveRowLiterals('organ', roweditor, bundledData, rec, i, MA.BioSourceLoad);
};

MA.BioSource = {
    baseCls: 'x-plain',
    border: false,
    frame: false,
    layout: 'border',
    defaults: {
        bodyStyle: 'padding:15px;background:transparent;'
    },
    items: [
        {
            title: 'Source Details',
            region: 'center',
            collapsible: false,
            layout: 'anchor',
            autoScroll: true,
            minSize: 75,
            items: [
                    {
                        xtype: 'panel',
                        layout: 'column',
                        border: false,
                        bodyStyle: 'padding:5px;background:transparent;',

                        items: [
                            { //column 1
                                width: 350,
                                layout: 'form',
                                border: false,
                                bodyStyle: 'padding:5px;background:transparent;',
                                items: [
                                {
                                    xtype: 'combo', width: 150,
                                    fieldLabel: 'Source type',
                                    id: 'sourceType',
                                    name: 'typeText',
                                    editable: false,
                                    forceSelection: true,
                                    displayField: 'value',
                                    valueField: 'key',
                                    hiddenName: 'sourceTypeValue',
                                    lazyRender: true,
                                    value: '1',
                                    mode: 'local',
                                    allowBlank: false,
                                    typeAhead: false,
                                    triggerAction: 'all',
                                    listWidth: 230,
                                    store: new Ext.data.ArrayStore({
                                                               fields: ['value', 'key'],
                                                               data: [['Microbial', 1],
                                                                       ['Plant', 2],
                                                                       ['Animal', 3],
                                                                       ['Human', 4],
                                                                       ['Synthetic', 5],
                                                                       ['Other', 6]]
                                                               }),
                                    listeners: {
                                        'select': MA.SourceTypeSelect
                                    }
                                },
                                {
                                    fieldLabel: 'NCBI ID',
                                    id: 'sourceNCBI',
                                    xtype: 'textfield'
                                },
                                { xtype: 'fieldset',
                                title: 'Microbial Information',
                                id: 'organismBioSourceMicrobialFieldset',
                                autoHeight: true,
                                labelWidth: 150,
                                items: [
                                        { xtype: 'textfield', fieldLabel: 'Genus', id: 'microbial_genus' },
                                        { xtype: 'textfield', fieldLabel: 'Species', id: 'microbial_species' },
                                        { xtype: 'textfield', fieldLabel: 'Culture collection ID', id: 'microbial_culture' },
                                        { xtype: 'textfield', fieldLabel: 'Media', id: 'microbial_media' },
                                        { xtype: 'textfield', fieldLabel: 'Fermentation vessel', id: 'microbial_vessel' },
                                        { xtype: 'textfield', fieldLabel: 'Fermentation mode', id: 'microbial_mode' },
                                        { xtype: 'numberfield', fieldLabel: 'Innoculation density', id: 'microbial_density', maxValue: 9999.99 },
                                        { xtype: 'numberfield', fieldLabel: 'Fermentation volume', id: 'microbial_volume', maxValue: 9999.99 },
                                        { xtype: 'numberfield', fieldLabel: 'Temperature', id: 'microbial_temperature', maxValue: 9999.99 },
                                        { xtype: 'numberfield', fieldLabel: 'Agitation', id: 'microbial_agitation', maxValue: 9999.99 },
                                        { xtype: 'numberfield', fieldLabel: 'pH', id: 'microbial_ph', maxValue: 9999.99 },
                                        { xtype: 'textfield', fieldLabel: 'Gas type', id: 'microbial_gastype' },
                                        { xtype: 'numberfield', fieldLabel: 'Gas flow rate', id: 'microbial_flowrate', maxValue: 9999.99 },
                                        { xtype: 'textfield', fieldLabel: 'Gas delivery method', id: 'microbial_delivery' }
                                        ]
                                },
                                { xtype: 'fieldset',
                                title: 'Plant Information',
                                id: 'organismBioSourcePlantFieldset',
                                autoHeight: true,
                                labelWidth: 150,
                                items: [
                                        { xtype: 'textfield', fieldLabel: 'Development stage', id: 'plant_development_stage' }
                                        ]
                                },
                                { xtype: 'fieldset',
                                title: 'Animal Information',
                                id: 'organismBioSourceAnimalFieldset',
                                autoHeight: true,
                                //hidden:true,
                                items: [

                                    { xtype: 'combo',
                                        fieldLabel: 'Gender',
                                        id: 'animalGender',
                                        width: 150,
                                        name: 'genderText',
                                        editable: false,
                                        forceSelection: true,
                                        displayField: 'value',
                                        valueField: 'key',
                                        hiddenName: 'gender',
                                        lazyRender: true,
                                        allowBlank: false,
                                        mode: 'local',
                                        typeAhead: false,
                                        triggerAction: 'all',
                                        listWidth: 230,
                                        store: new Ext.data.ArrayStore({
                                                                        fields: ['value', 'key'],
                                                                        data: [['Male', 'M'],
                                                                                ['Female', 'F'],
                                                                                ['Unknown', 'U']]
                                                                        })
                                    },
                                    { xtype: 'numberfield', fieldLabel: 'Age', id: 'animalAge', maxValue: 9999},
                                    { xtype: 'combo', width: 150,
                                        fieldLabel: 'Parental line',
                                        editable: true,
                                        id: 'animalParentalLine',
                                        displayField: 'value',
                                        valueField: 'key',
                                        forceSelection: false,
                                        hiddenName: 'node',
                                        lazyRender: true,
                                        allowBlank: false,
                                        typeAhead: false,
                                        triggerAction: 'all',
                                        listWidth: 230,
                                        store: animalComboStore
                                        },
                                        { xtype: 'textfield', fieldLabel: 'Location', id: 'animal_location' }
                                ]
                            },
                            { xtype: 'fieldset',
                            title: 'Human Information',
                            id: 'organismBioSourceHumanFieldset',
                            autoHeight: true,
                            //hidden:true,
                            items: [

                                    { xtype: 'combo',
                                    fieldLabel: 'Gender',
                                    id: 'humanGender',
                                    editable: false,
                                    width: 150,
                                    forceSelection: true,
                                    displayField: 'value',
                                    valueField: 'key',
                                    hiddenName: 'node',
                                    lazyRender: true,
                                    allowBlank: false,
                                    typeAhead: false,
                                    mode: 'local',
                                    triggerAction: 'all',
                                    listWidth: 230,
                                    store: new Ext.data.ArrayStore({
                                                                   fields: ['value', 'key'],
                                                                   data: [['Male', 'M'],
                                                                           ['Female', 'F'],
                                                                           ['Unknown', 'U']]
                                                                   })

                                    },
                                    { xtype: 'datefield', fieldLabel: 'Date of birth', id: 'human_dob', format: 'd/m/Y', width: 150},
                                    { xtype: 'numberfield', fieldLabel: 'BMI', id: 'human_bmi', maxValue: 9999.99 },
                                    { xtype: 'textfield', fieldLabel: 'Diagnosis', id: 'human_diagnosis' },
                                    { xtype: 'textfield', fieldLabel: 'Location', id: 'human_location' }
                                    ]
                            }
                            ]
                        },
                        { //column 2
                            width: 400,
                            layout: 'form',
                            border: false,
                            bodyStyle: 'padding:5px;background:transparent;',
                            items: [
                                {xtype: 'textarea', fieldLabel: 'Notes', id: 'sourceInfo', width: 240, height: 300 }
                            ]
                        }
                    ]
                },
                { xtype: 'grid',
                    id: 'organs',
                    style: 'margin-top:10px;margin-bottom:10px;',
                    title: 'Organs/Parts',
                    border: true,
                    height: 200,
                    trackMouseOver: false,
                    plugins: [new Ext.ux.grid.MARowEditor({saveText: 'Update', errorSummary: false, listeners: {'afteredit': MA.SaveOrganRow}})],
                    sm: new Ext.grid.RowSelectionModel(),
                    viewConfig: {
                        forceFit: true,
                        autoFill: true
                    },
                    tbar: [{
                        text: 'Add Organ/Part',
                        cls: 'x-btn-text-icon',
                        icon: 'static/images/add.png',
                        handler: function() {
                           MA.CRUDSomething('create/organ/', {'experiment_id': MA.ExperimentController.currentId(), 'name': 'Unknown'}, MA.BioSourceLoad);
                        }
                        },
                        {
                        text: 'Remove Organ/Part',
                        cls: 'x-btn-text-icon',
                        icon: 'static/images/delete.png',
                        handler: function() {
                            var grid = Ext.getCmp('organs');
                            var delIds = [];

                            var selections = grid.getSelectionModel().getSelections();
                            if (!Ext.isArray(selections)) {
                                selections = [selections];
                            }

                           for (var index = 0; index < selections.length; index++) {
                                if (!Ext.isObject(selections[index])) {
                                    continue;
                                }

                                delIds.push(selections[index].data.id);
                            }

                           for (var i = 0; i < delIds.length; i++) {
                           MA.CRUDSomething('delete/organ/' + delIds[i], {}, MA.BioSourceLoad);
                            }
                        }
                        }
                    ],
                    columns: [
                        { header: "Name", sortable: false, menuDisabled: true, editor: new Ext.form.ComboBox({
                                editable: true,
                                forceSelection: false,
                                displayField: 'value',
                                valueField: undefined,
                                hiddenName: 'tissue',
                                lazyRender: true,
                                allowBlank: false,
                                typeAhead: false,
                                triggerAction: 'all',
                                listWidth: 230,
                                store: organNameComboStore
                            }), dataIndex: 'name' },
                        { header: "Abbrev", sortable: false, menuDisabled: true, editor: new Ext.form.TextField({
                                editable: true,
                                forceSelection: false,
                                displayField: 'value',
                                valueField: undefined,
                                hiddenName: 'abbrevValue',
                                lazyRender: true,
                                allowBlank: true,
                                typeAhead: false,
                                triggerAction: 'all',
                                listWidth: 230
                            }), dataIndex: 'abbreviation'
                        },
                        { header: "Detail", sortable: false, menuDisabled: true, editor: new Ext.form.TextField({
                                editable: true,
                                forceSelection: false,
                                displayField: 'value',
                                valueField: undefined,
                                hiddenName: 'detailValue',
                                lazyRender: true,
                                allowBlank: true,
                                typeAhead: false,
                                triggerAction: 'all',
                                listWidth: 230
                            }), dataIndex: 'detail'
                        }
                    ],
                    store: organStore
                }
            ]
        }
    ]
};

