require 'rubygems'
require 'hpricot'
require 'faster_csv'
require 'optparse'
require 'fileutils'
require 'open-uri'
require 'time'
require 'pp'

module Scrapable
  include FileUtils
  class NoDataForYearError < ::StandardError 
    def initialize(year, msg)
      super "Unable to parse #{year}: #{msg}"
    end
  end
  
  def self.included(base)
    base.extend(self)
  end
  
  def options
    @options ||= {
      :years => [], 
      :chambers => []
    }
  end
  
  def add_bill(bill_hash)
    @legislation_csv << bill_hash
  end
  
  def add_bill_version(version_hash)
    @bill_versions_csv << version_hash
  end
  
  def add_sponsorship(sponsorship_hash)
    @sponsorships_csv << sponsorship_hash
  end
  
  def add_action(action_hash)
    @actions_csv << action_hash
  end
    
  def run
    opts = OptionParser.new do |o|
      o.on("-y", "--years [YEARS]", "Years to parse") {|opt| options[:years] = opt}
      o.on(nil,  "--all", "Parse from 1969...2009") {|opt| options[:years] << 1969...2009}              
      o.on(nil,  "--upper", "Parse upper chamber") {|opt| options[:chambers] << 'upper'}  
      o.on(nil,  "--lower", "Parse lower chamber") {|opt| options[:chambers] << 'lower'}              
    end.parse!
    
    setup_data_directories
    years = options[:years]
    options[:years] = years.kind_of?(String) ? years.strip.split(/\s+|,/i).compact.reject {|y| y.empty?} : years
    options[:chambers].each do |chamber|
      options[:years].each do |year|
        begin
          scrape_bills(chamber, year)
        rescue StandardError => e
          raise NoDataForYearError.new(year, e)
        end
      end
    end
  end
  
  private
  def setup_data_directories
    state_dir = File.join(File.dirname(__FILE__), '..', '..', 'data', state)
    mkdir(state_dir) unless File.exists?(state_dir)
    common_headers = [:bill_state, :bill_chamber, :bill_session, :bill_id]
    headers = {
      :legislation    => common_headers + [:bill_name],
      :bill_versions  => common_headers + [:version_name, :version_url],
      :actions        => common_headers + [:action_chamber, :action_text, :action_date],
      :sponsorships   => common_headers + [:sponsor_type, :sponsor_name]
    }
    
    %w(legislation actions bill_versions sponsorships).each do |type|
      csv = FasterCSV.open(File.join(state_dir, "#{type}.csv"), 'w', { 
        :headers => headers[type.to_sym],
        :skip_blanks => true
      })
      self.instance_variable_set("@#{type}_csv", csv)
    end
  end
end