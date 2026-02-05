# coding: utf-8
""" Unit tests for ibflex.parser module """

# PEP 563 compliance
# https://www.python.org/dev/peps/pep-0563/#resolving-type-hints-at-runtime
from __future__ import annotations

import unittest
from unittest.mock import patch, sentinel
import xml.etree.ElementTree as ET
import datetime
import decimal
import enum
from typing import Tuple, Optional
import functools

from ibflex import parser, Types, enums


@patch("ibflex.parser.parse_element_container")
@patch("ibflex.parser.parse_data_element")
class ParseElementTestCase(unittest.TestCase):
    """FlexStatements, elements w/o attributes go to parse_element_container().
    Everything else goes to parse_data_element().
    """
    def testFlexStatements(self, mock_parse_data, mock_parse_container):
        mock_parse_container.return_value = sentinel.TUPLE
        mock_parse_data.return_value = sentinel.FLEX_ELEMENT
        #  Elements without attributes get routed to parse_element_container()

        #  Elements with attributes get routed to parse_data_element()
        elem = ET.Element("FlexStatement", attrib={"foo": "bar"})
        output = parser.parse_element(elem)
        self.assertEqual(output, sentinel.FLEX_ELEMENT)

        #  ...except for <FlexStatements>, which gets routed to
        #  parse_element_container()
        elem = ET.Element("FlexStatements", attrib={"count": "2"})
        ET.SubElement(elem, "FooBar")
        ET.SubElement(elem, "FooBar")
        output = parser.parse_element(elem)
        mock_parse_container.assert_called_with(elem)
        self.assertEqual(output, sentinel.TUPLE)

        #  <FlexStatements> missing count throws an FlexParserError.
        elem = ET.Element("FlexStatements")
        with self.assertRaises(parser.FlexParserError):
            parser.parse_element(elem)

        # Empty <FlexStatements> is legal; returns an empty tuple.
        elem = ET.Element("FlexStatements", attrib={"count": "0"})
        output = parser.parse_element(elem)
        self.assertEqual(output, sentinel.TUPLE)

        # <FlexStatements> count attr must match # of contained elements
        elem = ET.Element("FlexStatements", attrib={"count": "2"})
        ET.SubElement(elem, "FooBar")
        with self.assertRaises(parser.FlexParserError):
            parser.parse_element(elem)

    def testEmptyAttributes(self, mock_parse_data, mock_parse_container):
        mock_parse_container.return_value = sentinel.TUPLE
        mock_parse_data.return_value = sentinel.FLEX_ELEMENT

        attrib = {"foo": "bar"}

        elem0 = ET.Element("FlexStatement")
        output0 = parser.parse_element(elem0)
        mock_parse_container.assert_called_with(elem0)
        self.assertEqual(output0, sentinel.TUPLE)

        elem1 = ET.Element("FlexStatement", attrib=attrib)
        output1 = parser.parse_element(elem1)
        self.assertEqual(output1, sentinel.FLEX_ELEMENT)


@patch("ibflex.parser.parse_data_element")
class ParseElementContainerTestCase(unittest.TestCase):
    def testBasic(self, mock_parse_data_element):
        """parse_element_container() returns parse_data_element() for each child.
        """
        elem = ET.Element("Foo")
        ET.SubElement(elem, "Bar")
        ET.SubElement(elem, "Bar")

        mock_parse_data_element.side_effect = range(10)
        output = parser.parse_element_container(elem)
        self.assertEqual(output, (0, 1))

    def testFxPositions(self, mock_parse_data_element):
        """parse_element_container() concatenates <FxPositions> grandchildren.
        """
        mock_parse_data_element.return_value = sentinel.FLEX_ELEMENT

        #  <FxPositions> with no children returns an empty tuple
        elem = ET.Element("FxPositions")
        output = parser.parse_element_container(elem)
        self.assertEqual(output, ())

        #  <FxPositions> with one <FxLots> child returns parse_data_element()
        #  for each <FxLot> grandchild.
        child = ET.SubElement(elem, "Bar")
        ET.SubElement(child, "Baz")
        ET.SubElement(child, "Baz")
        ET.SubElement(child, "Baz")

        output = parser.parse_element_container(elem)
        self.assertEqual(output, (sentinel.FLEX_ELEMENT, )*3)

        #  FxPositions with multiple <FxLots> children concatenates all
        #  <FxLot> grandchildren into a flat tuple.
        sibling = ET.SubElement(elem, "Bar")
        ET.SubElement(sibling, "Baz")
        ET.SubElement(sibling, "Baz")
        ET.SubElement(sibling, "Baz")

        output = parser.parse_element_container(elem)
        self.assertEqual(output, (sentinel.FLEX_ELEMENT, )*6)


class ParseDataElementTestCase(unittest.TestCase):
    def testContainedElements(self):
        #  Only FlexQueryResponse & FlexStatement may have contained elements.
        pass


class ParseElementAttrTestCase(unittest.TestCase):
    def testBasicType(self):
        """parse_element_attr(): class attribute type hint controls parsing."""

        class TestClass:
            foo: str
            bar: int
            baz: bool
            datetime: datetime.datetime
            date: datetime.date
            time: datetime.time
            sequence: Tuple[str, ...]

        #  Return (attr_name, type-converted value)

        #  int
        self.assertEqual(
            parser.parse_element_attr(TestClass, "foo", "1"),
            ("foo", "1")
        )
        self.assertEqual(
            parser.parse_element_attr(TestClass, "bar", "1"),
            ("bar", 1)
        )

        #  bool
        self.assertEqual(
            parser.parse_element_attr(TestClass, "foo", "Y"),
            ("foo", "Y")
        )
        self.assertEqual(
            parser.parse_element_attr(TestClass, "baz", "Y"),
            ("baz", True)
        )

        #  datetime vs date
        self.assertEqual(
            parser.parse_element_attr(TestClass, "datetime", "20100411"),
            ("datetime", datetime.datetime(2010, 4, 11))
        )
        self.assertEqual(
            parser.parse_element_attr(TestClass, "date", "20100411"),
            ("date", datetime.date(2010, 4, 11))
        )

        #  time
        self.assertEqual(
            parser.parse_element_attr(TestClass, "foo", "152559"),
            ("foo", "152559")
        )
        self.assertEqual(
            parser.parse_element_attr(TestClass, "time", "152559"),
            ("time", datetime.time(15, 25, 59))
        )

    def testOptional(self):

        class TestClass:
            string: str
            optstring: Optional[str]
            integer: int
            optinteger: Optional[int]
            boolean: bool
            optboolean: Optional[bool]
            decimal: decimal.Decimal
            optdecimal: Optional[decimal.Decimal]
            datetime: datetime.datetime
            optdatetime: Optional[datetime.datetime]
            date: datetime.date
            optdate: Optional[datetime.date]
            time: datetime.time
            opttime: Optional[datetime.time]

        #  Strings always return None if empty, whether or not hinted Optional.
        self.assertEqual(
            parser.parse_element_attr(TestClass, "string", ""),
            ("string", None)
        )
        self.assertEqual(
            parser.parse_element_attr(TestClass, "optstring", ""),
            ("optstring", None)
        )

        #  Other basic types return None for empty string if hinted Optional,
        #  otherwise raise FlexParseError for input empty string.
        self.assertEqual(
            parser.parse_element_attr(TestClass, "optinteger", ""),
            ("optinteger", None)
        )
        with self.assertRaises(parser.FlexParserError):
            parser.parse_element_attr(TestClass, "integer", ""),

        self.assertEqual(
            parser.parse_element_attr(TestClass, "optboolean", ""),
            ("optboolean", None)
        )
        with self.assertRaises(parser.FlexParserError):
            parser.parse_element_attr(TestClass, "boolean", ""),

        self.assertEqual(
            parser.parse_element_attr(TestClass, "optdecimal", ""),
            ("optdecimal", None)
        )
        with self.assertRaises(parser.FlexParserError):
            parser.parse_element_attr(TestClass, "decimal", ""),

        self.assertEqual(
            parser.parse_element_attr(TestClass, "optdatetime", ""),
            ("optdatetime", None)
        )
        with self.assertRaises(parser.FlexParserError):
            parser.parse_element_attr(TestClass, "datetime", ""),

        self.assertEqual(
            parser.parse_element_attr(TestClass, "optdate", ""),
            ("optdate", None)
        )
        with self.assertRaises(parser.FlexParserError):
            parser.parse_element_attr(TestClass, "date", ""),

        self.assertEqual(
            parser.parse_element_attr(TestClass, "opttime", ""),
            ("opttime", None)
        )
        with self.assertRaises(parser.FlexParserError):
            parser.parse_element_attr(TestClass, "time", ""),

    def testSequence(self):
        """parse_element_attr(): Sequence is always converted to tuple."""

        class TestClass:
            foo: str
            sequence: Tuple[str, ...]

        self.assertEqual(
            parser.parse_element_attr(TestClass, "foo", "A,B,C"),
            ("foo", "A,B,C")
        )
        self.assertEqual(
            parser.parse_element_attr(TestClass, "sequence", "A,B,C"),
            ("sequence", ("A", "B", "C"))
        )

        # Sequence null data parses as empty tuple
        self.assertEqual(
            parser.parse_element_attr(TestClass, "sequence", ""),
            ("sequence", ())
        )

    def testEnum(self):
        """parse_element_attr() converts Enum values to names.
        """

        class TestEnum(enum.Enum):
            FOO = "1"
            BAR = "2"

        class TestClass:
            foobar: Optional[TestEnum] = None

        #  Enum must be added to ATTRIB_CONVERTERS in order to be converted.
        with patch.dict(
            "ibflex.parser.ATTRIB_CONVERTERS",
            {"Optional[TestEnum]": functools.partial(parser.convert_enum, Type=TestEnum)}
        ):
            self.assertEqual(
                parser.parse_element_attr(TestClass, "foobar", "1"),
                ("foobar", TestEnum.FOO)
            )
            self.assertEqual(
                parser.parse_element_attr(TestClass, "foobar", "2"),
                ("foobar", TestEnum.BAR)
            )

            #  Illegal enum values raise FlexParserError
            with self.assertRaises(parser.FlexParserError):
                parser.parse_element_attr(TestClass, "foobar", "3")

    def testCurrency(self):
        """parse_element_attr() checks attributes named 'currency' vs ISO4217.
        """

        class TestClass:
            fooCurREncY: str
            notcurrencies: str

        self.assertEqual(
            parser.parse_element_attr(TestClass, "notcurrencies", "FOO"),
            ("notcurrencies", "FOO")
        )
        with self.assertRaises(parser.FlexParserError):
            parser.parse_element_attr(TestClass, "fooCurREncY", "FOO")


class ConverterFunctionTestCase(unittest.TestCase):
    def testConvertString(self):
        self.assertEqual(parser.convert_string("Foo"), "Foo")

        #  Empty string returns None.
        self.assertEqual(parser.convert_string(""), None)

    def testConvertInt(self):
        self.assertEqual(parser.convert_int("12"), 12)

        #  Empty string raises FlexParserError.
        with self.assertRaises(parser.FlexParserError):
            parser.convert_int("")

    def testConvertBool(self):
        """ Legal boolean values are 'Y'/'N' or 'Yes'/'No' """
        self.assertEqual(parser.convert_bool("Y"), True)
        self.assertEqual(parser.convert_bool("N"), False)
        self.assertEqual(parser.convert_bool("Yes"), True)
        self.assertEqual(parser.convert_bool("No"), False)

        #  Empty string raises FlexParserError.
        with self.assertRaises(parser.FlexParserError):
            parser.convert_bool("")

        # Illegal input raises FlexParserError.
        for bogus in ("y", "n", True, False, 1, 0, "YES", "NO", "yes", "no"):
            with self.assertRaises(parser.FlexParserError):
                parser.convert_bool(bogus)

    def testConvertDecimal(self):
        """ Decimal strings may include comma place delimiters """
        dec = parser.convert_decimal("2,345,678.99")
        self.assertEqual(dec, decimal.Decimal("2345678.99"))

        #  Empty string raises FlexParserError.
        with self.assertRaises(parser.FlexParserError):
            parser.convert_decimal("")

    def testConvertDate(self):
        """Legal date fmt yyyyMMdd, yyyy-MM-dd, MM/dd/yyyy, MM/dd/yy, dd-MMM-yy

        Empty string returns None.
        """
        for string in (
            "20160229", "2016-02-29", "02/29/2016", "02/29/16", "29-feb-16"
        ):
            date = parser.convert_date(string)
            self.assertEqual(date, datetime.date(2016, 2, 29))

        # Illegal dates fail with FlexParserError
        with self.assertRaises(parser.FlexParserError):
            parser.convert_date("20150229")

        #  Empty string raises FlexParserError.
        with self.assertRaises(parser.FlexParserError):
            parser.convert_date("")

    def testConvertTime(self):
        """Legal time formats: HHmmss, HH:mm:ss"""
        for string in (
            "143529", "14:35:29",
        ):
            time = parser.convert_time(string)
            self.assertEqual(time, datetime.time(14, 35, 29))

        # Illegal times fail with FlexParserError
        with self.assertRaises(parser.FlexParserError):
            parser.convert_time("240000")  # datetime.time has no leap seconds

        #  Empty string raises FlexParserError.
        with self.assertRaises(parser.FlexParserError):
            parser.convert_time("")

    def testConvertDateTime(self):
        """Legal datetime formats: date & time joined by {";", ",", " ", ""}
        """
        for datestr in (
            "20160229", "2016-02-29", "02/29/2016", "02/29/16", "29-feb-16"
        ):
            for timestr in (
                "143529", "14:35:29",
            ):
                for sep in (";", ",", " ", ""):
                    datetimestr = sep.join((datestr, timestr))
                    datetime_ = parser.convert_datetime(datetimestr)
                    self.assertEqual(
                        datetime_, datetime.datetime(2016, 2, 29, 14, 35, 29)
                    )

        #  Plain dates (without time) also get converted to datetime.
        self.assertEqual(
            parser.convert_datetime("20160229"), datetime.datetime(2016, 2, 29)
        )

        #  Illegal datetimes fail with FlexParserError
        with self.assertRaises(parser.FlexParserError):
            parser.convert_datetime("20150229")

        #  Empty string raises FlexParserError.
        with self.assertRaises(parser.FlexParserError):
            parser.convert_datetime("")

        #  Hacks to work around messed-up formats from old data.
        self.assertEqual(
            parser.convert_datetime("2010-01-04T15:37:49-05:00"),
            datetime.datetime(2010, 1, 4, 15, 37, 49)
        )
        self.assertEqual(
            parser.convert_datetime("2009-12-23, 20:25:00"),
            datetime.datetime(2009, 12, 23, 20, 25)
        )
        self.assertEqual(
            parser.convert_datetime("2010-01-08, 14:02:30"),
            datetime.datetime(2010, 1, 8, 14, 2, 30)
        )

    def testConvertSequence(self):
        """String sequences can be comma- or semicolon-delimited.
        """
        self.assertEqual(parser.convert_sequence("Foo,Bar"), ("Foo", "Bar"))
        self.assertEqual(parser.convert_sequence("Foo;Bar"), ("Foo", "Bar"))

        #  Single element (undelimited) still gets converted to tuple
        self.assertEqual(parser.convert_sequence("Foobar"), ("Foobar", ))

        #  Empty string returns empty tuple.
        self.assertEqual(parser.convert_sequence(""), ())

    def testConvertEnum(self):
        """convert_enum() looks up by value not name.
        """
        class TestEnum(enum.Enum):
            FOO = "1"
            BAR = "2"

        self.assertEqual(parser.convert_enum(TestEnum, "1"), TestEnum.FOO)
        self.assertEqual(parser.convert_enum(TestEnum, "2"), TestEnum.BAR)

        #  Empty string returns None.
        self.assertEqual(parser.convert_enum(TestEnum, ""), None)

        #  Old and new versions of enum values work.
        self.assertEqual(
            parser.convert_enum(enums.CashAction, "Deposits/Withdrawals"),
            enums.CashAction.DEPOSITWITHDRAW,
        )
        self.assertEqual(
            parser.convert_enum(enums.CashAction, "Deposits & Withdrawals"),
            enums.CashAction.DEPOSITWITHDRAW,
        )

        self.assertEqual(
            parser.convert_enum(enums.TransferType, "ACAT"),
            enums.TransferType.ACATS,
        )
        self.assertEqual(
            parser.convert_enum(enums.TransferType, "ACATS"),
            enums.TransferType.ACATS,
        )

    def testMakeOptional(self):
        """make_optional() wraps converter functions to return None for empty string.
        """
        opt = parser.make_optional

        self.assertEqual(opt(parser.convert_int)("12"), 12)
        self.assertEqual(opt(parser.convert_int)(""), None)

        self.assertEqual(opt(parser.convert_bool)("Y"), True)
        self.assertEqual(opt(parser.convert_bool)("N"), False)
        self.assertEqual(opt(parser.convert_bool)(""), None)

        self.assertEqual(
            opt(parser.convert_decimal)("2,345,678.99"),
            decimal.Decimal("2345678.99")
        )
        self.assertEqual(
            opt(parser.convert_decimal)(""), None
        )

        for string in (
            "20160229", "2016-02-29", "02/29/2016", "02/29/16", "29-feb-16"
        ):
            self.assertEqual(
                opt(parser.convert_date)(string),
                datetime.date(2016, 2, 29)
            )
        self.assertEqual(
            opt(parser.convert_date)(""), None
        )

        for string in (
            "143529", "14:35:29",
        ):
            self.assertEqual(
                opt(parser.convert_time)(string),
                datetime.time(14, 35, 29)
            )
        self.assertEqual(
            opt(parser.convert_time)(""), None
        )

        for datestr in (
            "20160229", "2016-02-29", "02/29/2016", "02/29/16", "29-feb-16"
        ):
            for timestr in (
                "143529", "14:35:29",
            ):
                for sep in (";", ",", " ", ""):
                    datetimestr = sep.join((datestr, timestr))
                    self.assertEqual(
                        opt(parser.convert_datetime)(datetimestr),
                        datetime.datetime(2016, 2, 29, 14, 35, 29)
                    )
        self.assertEqual(
            opt(parser.convert_datetime)(""), None
        )


class UnknownAttributeToleranceTestCase(unittest.TestCase):
    """Tests for the unknown attribute tolerance feature.

    This feature allows the parser to silently ignore unknown XML attributes
    and element types, which is useful when Interactive Brokers adds new fields
    to their exports.
    """

    def setUp(self):
        """Ensure tolerance is off before each test."""
        parser.disable_unknown_attribute_tolerance()

    def tearDown(self):
        """Ensure tolerance is off after each test."""
        parser.disable_unknown_attribute_tolerance()

    def test_tolerance_default_off(self):
        """Tolerance is off by default."""
        self.assertFalse(parser._UNKNOWN_ATTRIBUTE_TOLERANCE)

    def test_enable_disable(self):
        """enable/disable functions toggle the flag correctly."""
        self.assertFalse(parser._UNKNOWN_ATTRIBUTE_TOLERANCE)
        parser.enable_unknown_attribute_tolerance()
        self.assertTrue(parser._UNKNOWN_ATTRIBUTE_TOLERANCE)
        parser.disable_unknown_attribute_tolerance()
        self.assertFalse(parser._UNKNOWN_ATTRIBUTE_TOLERANCE)

    def test_tolerance_functions_accessible_from_package(self):
        """The tolerance functions are accessible from the top-level ibflex package.

        On the original upstream ibflex package these functions do not exist,
        so calling ibflex.enable_unknown_attribute_tolerance() would raise
        AttributeError, providing a clear version guard.
        """
        import ibflex
        self.assertTrue(hasattr(ibflex, 'enable_unknown_attribute_tolerance'))
        self.assertTrue(hasattr(ibflex, 'disable_unknown_attribute_tolerance'))
        # Verify they are callable
        self.assertTrue(callable(ibflex.enable_unknown_attribute_tolerance))
        self.assertTrue(callable(ibflex.disable_unknown_attribute_tolerance))

    def test_unknown_attr_raises_without_tolerance(self):
        """Without tolerance, unknown XML attributes raise FlexParserError."""
        # AccountInformation with an unknown attribute "newIBField"
        elem = ET.fromstring(
            '<AccountInformation accountId="U123456" currency="USD" '
            'newIBField="some_value" />'
        )
        with self.assertRaises(parser.FlexParserError):
            parser.parse_data_element(elem)

    def test_unknown_attr_ignored_with_tolerance(self):
        """With tolerance enabled, unknown XML attributes are silently ignored."""
        parser.enable_unknown_attribute_tolerance()

        elem = ET.fromstring(
            '<AccountInformation accountId="U123456" currency="USD" '
            'newIBField="some_value" anotherNewField="42" />'
        )
        instance = parser.parse_data_element(elem)
        self.assertIsInstance(instance, Types.AccountInformation)
        self.assertEqual(instance.accountId, "U123456")
        self.assertEqual(instance.currency, "USD")
        # Unknown attributes are not present on the parsed object
        self.assertFalse(hasattr(instance, 'newIBField'))
        self.assertFalse(hasattr(instance, 'anotherNewField'))

    def test_known_attrs_still_parsed_with_tolerance(self):
        """With tolerance, known attributes are still correctly parsed."""
        parser.enable_unknown_attribute_tolerance()

        elem = ET.fromstring(
            '<AccountInformation accountId="U123456" acctAlias="test" '
            'currency="USD" name="Test User" dateOpened="2020-01-15" '
            'unknownField="ignored" />'
        )
        instance = parser.parse_data_element(elem)
        self.assertIsInstance(instance, Types.AccountInformation)
        self.assertEqual(instance.accountId, "U123456")
        self.assertEqual(instance.acctAlias, "test")
        self.assertEqual(instance.currency, "USD")
        self.assertEqual(instance.name, "Test User")
        import datetime
        self.assertEqual(instance.dateOpened, datetime.date(2020, 1, 15))

    def test_disable_restores_strict_behavior(self):
        """After disabling tolerance, unknown attributes raise errors again."""
        parser.enable_unknown_attribute_tolerance()

        elem = ET.fromstring(
            '<AccountInformation accountId="U123456" currency="USD" '
            'newIBField="some_value" />'
        )
        # Should succeed with tolerance on
        instance = parser.parse_data_element(elem)
        self.assertIsInstance(instance, Types.AccountInformation)

        parser.disable_unknown_attribute_tolerance()

        # Should fail with tolerance off
        with self.assertRaises(parser.FlexParserError):
            parser.parse_data_element(elem)

    def test_unknown_element_type_raises_without_tolerance(self):
        """Without tolerance, unknown XML element types raise AttributeError."""
        elem = ET.fromstring('<BrandNewReportType foo="bar" />')
        with self.assertRaises(AttributeError):
            parser.parse_data_element(elem)

    def test_unknown_element_type_returns_none_with_tolerance(self):
        """With tolerance, unknown element types return None."""
        parser.enable_unknown_attribute_tolerance()

        elem = ET.fromstring('<BrandNewReportType foo="bar" />')
        result = parser.parse_data_element(elem)
        self.assertIsNone(result)

    def test_unknown_elements_filtered_in_container(self):
        """With tolerance, unknown element types are filtered out of containers."""
        parser.enable_unknown_attribute_tolerance()

        container = ET.Element("Trades")
        # Add a known Trade element
        ET.SubElement(container, "Trade", attrib={
            "accountId": "U123456",
            "currency": "USD",
            "fxRateToBase": "1",
            "assetCategory": "STK",
            "symbol": "AAPL",
            "description": "APPLE INC",
            "conid": "265598",
            "tradeID": "123",
            "reportDate": "2020-01-15",
            "tradeDate": "2020-01-15",
            "quantity": "100",
            "tradePrice": "150.00",
            "tradeMoney": "15000.00",
            "proceeds": "-15000.00",
            "taxes": "0",
            "ibCommission": "-1.00",
            "ibCommissionCurrency": "USD",
            "netCash": "-15001.00",
            "buySell": "BUY",
        })
        # Add an unknown element type
        ET.SubElement(container, "BrandNewTradeType", attrib={
            "unknownField": "value"
        })

        result = parser.parse_element_container(container)
        # Only the known Trade should be in the result
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], Types.Trade)

    def test_full_parse_with_unknown_attrs(self):
        """Full round-trip: parse a FlexQueryResponse with unknown attributes."""
        parser.enable_unknown_attribute_tolerance()

        xml_data = (
            '<FlexQueryResponse queryName="test" type="AF">'
            '<FlexStatements count="1">'
            '<FlexStatement accountId="U123456" fromDate="2020-01-01" '
            'toDate="2020-12-31" period="Annual" '
            'whenGenerated="2021-01-01;120000" '
            'brandNewStatementAttr="surprise" />'
            '</FlexStatements>'
            '</FlexQueryResponse>'
        )
        response = parser.parse(xml_data.encode())
        self.assertIsInstance(response, Types.FlexQueryResponse)
        self.assertEqual(response.queryName, "test")
        self.assertEqual(len(response.FlexStatements), 1)
        stmt = response.FlexStatements[0]
        self.assertEqual(stmt.accountId, "U123456")

    def test_full_parse_unknown_attrs_fails_without_tolerance(self):
        """Without tolerance, unknown attributes in full parse raise errors."""
        xml_data = (
            '<FlexQueryResponse queryName="test" type="AF">'
            '<FlexStatements count="1">'
            '<FlexStatement accountId="U123456" fromDate="2020-01-01" '
            'toDate="2020-12-31" period="Annual" '
            'whenGenerated="2021-01-01;120000" '
            'brandNewStatementAttr="surprise" />'
            '</FlexStatements>'
            '</FlexQueryResponse>'
        )
        with self.assertRaises(parser.FlexParserError):
            parser.parse(xml_data.encode())

    def test_unknown_contained_element_in_statement(self):
        """With tolerance, unknown contained elements in FlexStatement are ignored."""
        parser.enable_unknown_attribute_tolerance()

        xml_data = (
            '<FlexQueryResponse queryName="test" type="AF">'
            '<FlexStatements count="1">'
            '<FlexStatement accountId="U123456" fromDate="2020-01-01" '
            'toDate="2020-12-31" period="Annual" '
            'whenGenerated="2021-01-01;120000">'
            '<BrandNewSection>'
            '<BrandNewItem foo="bar" />'
            '</BrandNewSection>'
            '</FlexStatement>'
            '</FlexStatements>'
            '</FlexQueryResponse>'
        )
        response = parser.parse(xml_data.encode())
        self.assertIsInstance(response, Types.FlexQueryResponse)
        self.assertEqual(len(response.FlexStatements), 1)
        self.assertEqual(response.FlexStatements[0].accountId, "U123456")

    def test_multiple_unknown_attrs_on_trade(self):
        """Unknown attributes on Trade elements are ignored with tolerance."""
        parser.enable_unknown_attribute_tolerance()

        elem = ET.fromstring(
            '<Trade accountId="U123456" currency="USD" fxRateToBase="1" '
            'assetCategory="STK" symbol="AAPL" description="APPLE INC" '
            'conid="265598" tradeID="123" reportDate="2020-01-15" '
            'tradeDate="2020-01-15" quantity="100" tradePrice="150.00" '
            'tradeMoney="15000.00" proceeds="-15000.00" taxes="0" '
            'ibCommission="-1.00" ibCommissionCurrency="USD" '
            'netCash="-15001.00" buySell="BUY" '
            'newField1="value1" newField2="value2" newField3="value3" />'
        )
        instance = parser.parse_data_element(elem)
        self.assertIsInstance(instance, Types.Trade)
        self.assertEqual(instance.symbol, "AAPL")
        self.assertEqual(instance.tradeID, "123")
        self.assertFalse(hasattr(instance, 'newField1'))


if __name__ == '__main__':
    unittest.main(verbosity=3)
