/*jslint vars: false, nomen: true, browser: true */
/*global $, console, alert, active_card, Wizard */


$.fn.serializeObject = function () {
    var o = {};
    var a = this.serializeArray();
    $.each(a, function() {
        if (o[this.name] !== undefined) {
            if (!o[this.name].push) {
                o[this.name] = [o[this.name]];
            }
            o[this.name].push(this.value || '');
        } else {
            o[this.name] = this.value || '';
        }
    });
    return o;
};


var EduidWizard = function (container_path, active_card, options) {

    var wizard = $(container_path).wizard(options),
        presentcard,
        newcard,
        show_alert = function (message, level) {
            var currentCard = wizard.getActiveCard();

            if (level === undefined) {
                level = 'error';
            }
            if (currentCard.el.find('div.alert.alert-' + level).length > 0) {
                currentCard.el.find('div.alert.alert-' + level).html(message);
            }
            else {
                currentCard.el.find('> h3').
                    before("<div class='alert alert-" + level + "'>" + message + "</div>");
            }
            setTimeout(function () {
                currentCard.el.find('div.alert').hide('slow').html("");
            }, 5000);
        }


    Wizard.prototype._onNextClick = function () {
        var jsondata,
            currentCard = this.getActiveCard(),
            step = currentCard.index;

        this.log("handling 'next' button click (custom method)");

        if (currentCard.index === (this._cards.length - 1)) {
            // This is the last card
            this.reset().close();

        } else if (currentCard.validate()) {
            jsondata = wizard.el.find('input, select').serializeObject();
            $.extend(jsondata, {
                step: currentCard.index,
                action: 'next_step'
            });
            $.ajax({
                url: this.args.submitUrl,
                data: jsondata,
                type: 'POST',
                success: function (data, textStatus, jqXHR){
                    if (data.status === 'ok') {
                        // go to next card
                        currentCard = wizard.incrementCard();
                    }
                    else if (data.status == 'failure') {
                        currentCard.el.find('.control-group').toggleClass("error", false);
                        currentCard.el.find('select, input, textarea').popover("destroy");

                        for(var input in data.data) {
                            var el = currentCard.el.find('[name=' + input + ']');
                            wizard.errorPopover(el, data.data[input]);
                            el.parent(".control-group").toggleClass("error", true);
                        }
                    }
                },
                error: function (event, jqXHR, ajaxSettings, thrownError) {
                    console.debug('Hey!, there are some errors here ' +
                                  thrownError);
                }
            });
        }
    };

    wizard.cancelButton.click(function (e) {
        $.ajax({
            url: wizard.args.submitUrl,
            data: {
                action: 'dismissed'
            },
            type: 'POST',
            success: function (data, textStatus, jqXHR){
                wizard.reset().close();
            },
            error: function (event, jqXHR, ajaxSettings, thrownError) {
                console.debug('Hey!, there are some errors here ' +
                              thrownError);
                wizard.close();
            }
        });
    });

    wizard.el.find('a[data-role=action]').click(function (e) {
        var action = $(e.target).attr('data-action'),
            jsondata = wizard.el.find('input, select').serializeObject(),
            currentCard = wizard.getActiveCard();

        $.extend(jsondata, {
            step: currentCard.index,
            action: action
        });
        $.ajax({
            url: options.submitUrl,
            data: jsondata,
            type: 'POST',
            success: function (data, textStatus, jqXHR){
                if (data.status === 'ok') {
                    // show a successs message
                    show_alert(data.text, 'success');
                }
                else if (data.status === 'error') {
                    // show a error message
                    show_alert(data.text);
                }
            },
            error: function (event, jqXHR, ajaxSettings, thrownError) {
                show_alert('Unexpected error, please retry later');
                console.debug('Hey!, there are some errors here ' +
                              thrownError);
            }
        });
        e.preventDefault();
    });

    wizard.show();
    if (active_card > 1) {
        presentcard = wizard._cards[0];
        presentcard.deselect();
        presentcard.markVisited();
        newcard = wizard.setCard(active_card-1);
        newcard.select();
    }

    return wizard;
};
