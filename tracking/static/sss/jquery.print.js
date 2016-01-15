/*  jQuery.print, version 1.0.3
 *  (c) Sathvik Ponangi, Doers' Guild
 * Licence: CC-By (http://creativecommons.org/licenses/by/3.0/)
 *--------------------------------------------------------------------------*/

(function($) {"use strict";
    // A nice closure for our definitions

    function getjQueryObject(string) {
        // Make string a vaild jQuery thing
        var jqObj = $("");
        try {
            jqObj = $(string).clone();
        } catch(e) {
            jqObj = $("<span />").html(string);
        }
        return jqObj;
    }

    function isNode(o) {
        /* http://stackoverflow.com/a/384380/937891 */
        return !!( typeof Node === "object" ? o instanceof Node : o && typeof o === "object" && typeof o.nodeType === "number" && typeof o.nodeName === "string");
    }

    function fillAndPrint(w,options,context,printFunction) {
        var  _fillAndPrint = function() {
            if ($(w.document).contents().find("#content_container").length == 0) {
                setTimeout(_fillAndPrint,100);
            } else {
                //get the page width and page height
                $(w.document).contents().find("body").append("<div id='mm_to_pixel'> style='height:1mm;display:none'></div>");
                var $mm_to_pixel = $(w.document).contents().find("#mm_to_pixel");
                $mm_to_pixel.width(w.page_width + "mm");
                var page_width = Math.floor($mm_to_pixel.width());
                $mm_to_pixel.height(w.page_height + "mm");
                var page_height = Math.floor($mm_to_pixel.height());
                $mm_to_pixel.remove();

                //compute the scale
                var scale = 1;
                if ((context.content_width / context.content_height) > (page_width / page_height)) {
                    scale = page_width / context.content_width;
                } else {
                    scale = page_height / context.content_height;
                }
                var scale_value = "scale(" + scale + "," + scale + ")";
        
                //set the scale 
                context.content.css("transform",scale_value);
                context.content.css("-ms-transform",scale_value);
                context.content.css("-webkit-transform",scale_value);
                context.content.css("-moz-transform",scale_value);
                context.content.css("-o-transform",scale_value);
                context.content.css("position","absolute");
        

                $(w.document).contents().find("#content_container").append(context.content);
                //fill the extra fields
                if (options.extra_fields != null) {
                    for (var key in options.extra_fields) {
                        if (options.extra_fields[key] == null) {
                            continue;
                        } else {
                            $(w.document).contents().find("#" + key).append(options.extra_fields[key]);
                        }
                    }
                }
    
                if (context.inline_css != null) $(w.document).contents().find('head').append($(context.inline_css));

                if (options.scale_selector != null) {
                    $(w.document).contents().find(options.scale_selector).css("transform",scale_value);
                    $(w.document).contents().find(options.scale_selector).css("-ms-transform",scale_value);
                    $(w.document).contents().find(options.scale_selector).css("-webkit-transform",scale_value);
                    $(w.document).contents().find(options.scale_selector).css("-moz-transform",scale_value);
                    $(w.document).contents().find(options.scale_selector).css("-o-transform",scale_value);
                }

                //position the content footer and header
                var $content_header = $(w.document).contents().find("#content_header");
                var $content_footer = $(w.document).contents().find("#content_footer");

                if ($content_header.length > 0) {
                    $content_header.width(context.content_width * scale);
                }
                if ($content_footer.length > 0) {
                    var content_offset = context.content.offset();
                    $content_footer.offset({top:content_offset.top + context.content_height * scale + 10 ,left:$content_header.offset().left});
                    $content_footer.width(context.content_width * scale);
                }
                printFunction();
            }
        };
        setTimeout(_fillAndPrint,1);
    }

    $.print = $.fn.print = function() {
        // Print a given set of elements
        var options, $this, self = this;

        if ( self instanceof $) {
            // Get the node if it is a jQuery object
            self = self.get(0);
        }

        if (isNode(self)) {
            // If `this` is a HTML element, i.e. for
            // $(selector).print()
            $this = $(self);
            if (arguments.length > 0) {
                options = arguments[0];
            }
        } else {
            if (arguments.length > 0) {
                // $.print(selector,options)
                $this = $(arguments[0]);
                if (isNode($this[0])) {
                    if (arguments.length > 1) {
                        options = arguments[1];
                    }
                } else {
                    // $.print(options)
                    options = arguments[0];
                    $this = $("html");
                }
            } else {
                // $.print()
                $this = $("html");
            }
        }

        // Default options
        var defaults = {
            no_print_selector : null,
            iframe : true,
            width: 420,
            height: 297,
            inline_css:null,
            scale_selector:null,
            extra_fields:null
            
        };
        var context = {};

        // Merge with user-options
        options = $.extend({}, defaults, (options || {}));
        //initialize the extra fields
        if (options.extra_fields != null) {
            for (var key in options.extra_fields) {
                if (options.extra_fields[key] == null) {
                    continue;
                } else if (typeof options.extra_fields[key] == 'string') {
                    if (options.extra_fields[key].trim().length == 0) {
                        options.extra_fields[key] = null;
                    } else {
                        options.extra_fields[key] = $("<span>" + options.extra_fields[key] + "</span>");
                    }
                } else if (typeof options.extra_fields[key] == 'number') {
                    options.extra_fields[key] = $("<span>" + options.extra_fields[key] + "</span>");
                } else if (options.extra_fields[key] instanceof jQuery) {
                    options.extra_fields[key] = options.extra_fields[key].clone();
                } else {
                    options.extra_fields[key] = $(options.extra_fields[key]).clone();
                }
            }
        }

        // Create a copy of the element to print
        context.content = $this.clone();
        //remove the non print elements
        if (options.no_print_selector != null) {
            context.content.find(options.no_print_selector).remove();
        }

        context.content_width = $this.width();
        context.content_height = $this.height();
        
        context.inline_css = " \
<style> \
    " + ( (options.inline_css == null)?"":options.inline_css) + " \
    @media print { \
        #map { \
            width: " + context.content_width + "px; \
            height: " + context.content_height + "px; \
        } \
</style>";

        var w, wdoc;
        if (options.iframe) {
            // Use an iframe for printing
            try {
                var $iframe = $("#print_frame");
                if ($iframe.length > 0) {
                    //remove the already existed print frame
                    $iframe.remove();
                }
                // Create a new iFrame if none is given
                $iframe = $('<iframe  id="print_frame" wmode="Opaque" src="/print"/>').prependTo('body').css({
                    "position" : "absolute",
                    "top" : 0,
                    "left" : 0
                });
                w = $iframe.get(0);
                w = w.contentWindow || w.contentDocument || w;
                fillAndPrint(w,options,context,function() {
                    w.focus();
                    w.print();
                    setTimeout(function() {
                        // Fix for IE
                        $("#print_frame").remove();
                        if (options.after_print != null) {
                            options.after_print();
                        }
                    }, 100);
                });
            } catch (e) {
                // Use the pop-up method if iframe fails for some reason
                w = window.open("/print");
                fillAndPrint(w,options,context,function() {
                    w.focus();
                    w.print();
                    w.close();
                    if (options.after_print != null) {
                        options.after_print();
                    }
                });
            }
        } else {
            // Use a new window for printing
            w = window.open("/print");
            fillAndPrint(w,options,context,function() {
                w.focus();
                w.print();
                w.close();
                if (options.after_print != null) {
                    options.after_print();
                }
            });
        }
        return this;
    };

})(jQuery);
