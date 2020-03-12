<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor xmlns="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="1.1.0" xmlns:xlink="http://www.w3.org/1999/xlink" xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.1.0/StyledLayerDescriptor.xsd" xmlns:se="http://www.opengis.net/se">
  <NamedLayer>
    <se:Name>radio_repeatertxcoverage</se:Name>
    <UserStyle>
      <se:Name>radio_repeatertxcoverage</se:Name>
      <se:FeatureTypeStyle>{% for c in gradients %}<se:Rule>
          <se:Name></se:Name>
          <se:Description>
              <se:Title>{% if c.0.0 == c.0.1 %}dn is '{{c.0.0}}'{% else %}dn between '{{c.0.0}}' and '{{c.0.1}}'{% endif %}</se:Title>
          </se:Description>
          <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">{% if c.0.0 == c.0.1 %}
            <ogc:PropertyIsEqualTo>
                  <ogc:PropertyName>dn</ogc:PropertyName>
                  <ogc:Literal>{{c.0.0}}</ogc:Literal>
            </ogc:PropertyIsEqualTo>{% else %}
            <ogc:And>
                <ogc:PropertyIsGreaterThanOrEqualTo>
                  <ogc:PropertyName>dn</ogc:PropertyName>
                  <ogc:Literal>{{c.0.0}}</ogc:Literal>
                </ogc:PropertyIsGreaterThanOrEqualTo>
                <ogc:PropertyIsLessThanOrEqualTo>
                  <ogc:PropertyName>dn</ogc:PropertyName>
                  <ogc:Literal>{{c.0.1}}</ogc:Literal>
                </ogc:PropertyIsLessThanOrEqualTo>
            </ogc:And>{% endif %}
          </ogc:Filter>
          <se:PolygonSymbolizer>
            <se:Fill>
              <se:SvgParameter name="fill">{{c.1}}</se:SvgParameter>
            </se:Fill>
          </se:PolygonSymbolizer>
        </se:Rule>{% endfor %}
      </se:FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
